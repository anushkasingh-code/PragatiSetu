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
    Calculates SHA-256 hash, checks for duplicates, stores file safely, and creates SourceReport record.
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
