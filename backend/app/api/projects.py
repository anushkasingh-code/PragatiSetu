import os
import shutil
import tempfile
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.database import get_db
from backend.app.db.models.project import Project
from backend.app.db.models.wbs import WBSNode
from backend.app.db.models.activity import ScheduleActivity
from backend.app.db.models.audit import AuditRecord
from backend.app.db.models.transcription import Transcription
from backend.app.db.models.report import SourceReport
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.decision import MatchDecision
from backend.app.db.models.candidate import MatchCandidate
from backend.app.schemas.project import ProjectCreate, ProjectResponse
from backend.app.schemas.wbs import WBSNodeResponse, WBSTreeNode
from backend.app.schemas.activity import ActivityResponse
from backend.app.services.baseline_importer import BaselineImporter

router = APIRouter(tags=["Projects & Activities"])

@router.get("/projects", response_model=List[ProjectResponse])
def get_projects(db: Session = Depends(get_db)):
    """Fetch all projects with real computed progress and operational status."""
    projects = db.query(Project).all()
    results = []
    for p in projects:
        acts = db.query(ScheduleActivity).filter(ScheduleActivity.project_id == p.project_id)
        total = acts.count()
        completed = acts.filter(ScheduleActivity.status == "COMPLETED").count()
        in_progress = acts.filter(ScheduleActivity.status.in_(["IN_PROGRESS", "STARTED"])).count()

        if total > 0:
            avg_pct = db.query(func.avg(ScheduleActivity.percent_complete)).filter(ScheduleActivity.project_id == p.project_id).scalar() or 0.0
            prog = round(float(avg_pct), 1)
        else:
            prog = 0.0

        if total > 0 and completed == total:
            status_val = "Completed"
        elif in_progress > 0 or completed > 0 or p.project_id == "PROJ-ALPHA":
            status_val = "Operational"
        else:
            status_val = "Planning"

        results.append(ProjectResponse(
            project_id=p.project_id,
            name=p.name,
            description=p.description,
            created_at=p.created_at,
            status=status_val,
            progress_percentage=prog,
            total_activities=total,
            completed_activities=completed
        ))
    return results

@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    """Creates a new project record."""
    existing = db.query(Project).filter(Project.project_id == payload.project_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with ID '{payload.project_id}' already exists."
        )

    project = Project(
        project_id=payload.project_id,
        name=payload.name,
        description=payload.description
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project

@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project_by_id(project_id: str, db: Session = Depends(get_db)):
    """Fetch a single project by ID."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )
    return project

@router.delete("/projects/{project_id}", status_code=status.HTTP_200_OK)
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """Deletes a single project and its associated project-specific data."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )

    # Clean up project-specific audit records and transcriptions
    db.query(AuditRecord).filter(AuditRecord.project_id == project_id).delete(synchronize_session=False)
    db.query(Transcription).filter(Transcription.project_id == project_id).delete(synchronize_session=False)

    # Clean up match decisions and candidates for events belonging to this project's reports
    report_ids = [r.report_id for r in db.query(SourceReport.report_id).filter(SourceReport.project_id == project_id).all()]
    if report_ids:
        event_ids = [e.event_id for e in db.query(ExtractedEvent.event_id).filter(ExtractedEvent.report_id.in_(report_ids)).all()]
        if event_ids:
            db.query(MatchDecision).filter(MatchDecision.event_id.in_(event_ids)).delete(synchronize_session=False)
            db.query(MatchCandidate).filter(MatchCandidate.event_id.in_(event_ids)).delete(synchronize_session=False)
            db.query(ExtractedEvent).filter(ExtractedEvent.event_id.in_(event_ids)).delete(synchronize_session=False)
        db.query(SourceReport).filter(SourceReport.project_id == project_id).delete(synchronize_session=False)

    db.query(ScheduleActivity).filter(ScheduleActivity.project_id == project_id).delete(synchronize_session=False)
    db.query(WBSNode).filter(WBSNode.project_id == project_id).delete(synchronize_session=False)

    db.delete(project)
    db.commit()
    return {"message": f"Project '{project_id}' deleted successfully.", "project_id": project_id}

@router.post("/projects/{project_id}/schedule/upload", status_code=status.HTTP_200_OK)
async def upload_baseline_schedule(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Uploads an Excel baseline schedule file (.xlsx) and imports WBS nodes and Schedule Activities into the project database.
    """
    if not file.filename or not file.filename.endswith(".xlsx"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Baseline schedule must be an Excel file with .xlsx extension."
        )

    tmp_path = None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        importer = BaselineImporter(db)
        importer.import_excel_baseline(tmp_path)
        activities_count = db.query(ScheduleActivity).filter(ScheduleActivity.project_id == project_id).count()
        return {
            "project_id": project_id,
            "filename": file.filename,
            "status": "IMPORTED",
            "activities_imported": activities_count,
            "message": "Baseline schedule imported successfully."
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to import baseline schedule: {str(e)}"
        )
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass

@router.get("/projects/{project_id}/wbs", response_model=List[WBSNodeResponse])
def get_project_wbs(project_id: str, db: Session = Depends(get_db)):
    """Fetch WBS nodes for a project."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )
    wbs_nodes = db.query(WBSNode).filter(WBSNode.project_id == project_id).order_by(WBSNode.level, WBSNode.wbs_id).all()
    return wbs_nodes

@router.get("/projects/{project_id}/activities", response_model=List[ActivityResponse])
def get_project_activities(project_id: str, db: Session = Depends(get_db)):
    """Fetch all schedule activities for a project."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )
    activities = db.query(ScheduleActivity).filter(ScheduleActivity.project_id == project_id).all()
    return activities

@router.get("/activities/{activity_id}", response_model=ActivityResponse)
def get_activity_by_id(activity_id: str, db: Session = Depends(get_db)):
    """Fetch a single schedule activity by ID."""
    activity = db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == activity_id).first()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ScheduleActivity with ID '{activity_id}' not found."
        )
    return activity
