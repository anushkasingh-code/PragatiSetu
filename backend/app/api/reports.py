from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.db.models.project import Project
from backend.app.db.models.report import SourceReport
from backend.app.schemas.report import ReportUploadResponse, ReportResponse
from backend.app.services.report_ingestion_service import ReportIngestionService
from backend.app.services.file_validator import ReportValidationError

router = APIRouter(tags=["Report Ingestion"])

def process_report_pipeline_end_to_end(report_id: str, db: Session):
    """
    Executes end-to-end event extraction, candidate matching, and auto-linking for a report.
    Guarantees that uploaded documents immediately populate the review queue and audit trail.
    """
    from backend.app.services.event_extraction_service import EventExtractionService
    from backend.app.services.decision_service import DecisionService
    from backend.app.services.progress_update_service import ProgressUpdateService
    from backend.app.db.models.report import SourceReport, ProcessingStatus

    try:
        extraction_service = EventExtractionService(db)
        updated_rep, events = extraction_service.extract_events_from_report(report_id)

        dec_service = DecisionService(db)
        update_service = ProgressUpdateService(db)

        for event in events:
            try:
                _, decision = dec_service.make_decision_for_event(event.event_id)
                if decision and decision.decision == "AUTO_LINK":
                    update_service.apply_event_progress(event.event_id)
            except Exception:
                continue

        updated_rep.processing_status = ProcessingStatus.COMPLETED.value
        db.commit()
        db.refresh(updated_rep)
        return updated_rep, events
    except Exception as e:
        try:
            db.rollback()
        except Exception:
            pass
        rep = db.query(SourceReport).filter(SourceReport.report_id == report_id).first()
        if rep:
            rep.processing_status = ProcessingStatus.FAILED.value
            rep.rejection_reason = str(e)
            db.commit()
        return rep, []

@router.post("/reports/upload", response_model=ReportUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_report(
    project_id: str = Form(...),
    file: UploadFile = File(...),
    report_date: str = Form(...),
    discipline: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Ingests and validates a field progress report (TXT, CSV, XLSX).
    Calculates SHA-256 hash, checks for duplicates, stores file safely, creates SourceReport record,
    and automatically executes end-to-end event extraction, candidate matching, and auto-linking.
    """
    content = await file.read()
    ingestion_service = ReportIngestionService(db)

    try:
        is_duplicate, result_payload, report_obj = ingestion_service.ingest_report(
            project_id=project_id,
            filename=file.filename or "unknown",
            content=content,
            report_date_input=report_date,
            discipline_input=discipline or ""
        )
        if not is_duplicate and report_obj:
            updated_rep, events = process_report_pipeline_end_to_end(report_obj.report_id, db)
            if updated_rep:
                result_payload["processing_status"] = updated_rep.processing_status

        return result_payload


    except ReportValidationError as ve:
        if ve.code == "INVALID_PROJECT":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=ve.message
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "valid": False,
                "errors": [{"code": ve.code, "message": ve.message}],
                "warnings": [],
                "details": ve.details
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during report ingestion: {str(e)}"
        )

@router.get("/reports/{report_id}", response_model=ReportResponse)
def get_report_by_id(report_id: str, db: Session = Depends(get_db)):
    """Fetch report metadata by report ID."""
    report = db.query(SourceReport).filter(SourceReport.report_id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found."
        )
    return report

@router.get("/projects/{project_id}/reports", response_model=List[ReportResponse])
def get_project_reports(project_id: str, db: Session = Depends(get_db)):
    """Fetch all uploaded reports for a project."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )
    reports = db.query(SourceReport).filter(SourceReport.project_id == project_id).order_by(SourceReport.created_at.desc()).all()
    return reports
