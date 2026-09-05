import os
import shutil
import tempfile
from typing import Dict, List, Tuple
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from sqlalchemy import case, func
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

def _project_status(project_id: str, total: int, completed: int, in_progress: int) -> str:
    if total > 0 and completed == total:
        return "Completed"
    if in_progress > 0 or completed > 0 or project_id == "PROJ-ALPHA":
        return "Operational"
    return "Planning"


def _empty_activity_stats() -> Tuple[int, int, int, float]:
    return 0, 0, 0, 0.0


def _load_project_activity_stats(db: Session, project_ids: List[str] | None = None) -> Dict[str, Tuple[int, int, int, float]]:
    """
    Aggregate activity counts and average percent_complete per project.
    Returns mapping: project_id -> (total, completed, in_progress, avg_pct)
    """
    query = db.query(
        ScheduleActivity.project_id,
        func.count(ScheduleActivity.activity_id).label("total"),
        func.coalesce(func.sum(case((ScheduleActivity.status == "COMPLETED", 1), else_=0)), 0).label("completed"),
        func.coalesce(
            func.sum(case((ScheduleActivity.status.in_(["IN_PROGRESS", "STARTED"]), 1), else_=0)),
            0,
        ).label("in_progress"),
        func.avg(ScheduleActivity.percent_complete).label("avg_pct"),
    )
    if project_ids is not None:
        if not project_ids:
            return {}
        query = query.filter(ScheduleActivity.project_id.in_(project_ids))
    rows = query.group_by(ScheduleActivity.project_id).all()
    stats: Dict[str, Tuple[int, int, int, float]] = {}
    for row in rows:
        stats[row.project_id] = (
            int(row.total or 0),
            int(row.completed or 0),
            int(row.in_progress or 0),
            float(row.avg_pct or 0.0),
        )
    return stats


def _build_project_response(project: Project, stats: Tuple[int, int, int, float] | None = None) -> ProjectResponse:
    total, completed, in_progress, avg_pct = stats if stats is not None else _empty_activity_stats()
    prog = round(avg_pct, 1) if total > 0 else 0.0
    return ProjectResponse(
        project_id=project.project_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        status=_project_status(project.project_id, total, completed, in_progress),
        progress_percentage=prog,
        total_activities=total,
        completed_activities=completed,
    )


@router.get("/projects", response_model=List[ProjectResponse])
def get_projects(db: Session = Depends(get_db)):
    """Fetch all projects with real computed progress and operational status."""
    projects = db.query(Project).all()
    stats_map = _load_project_activity_stats(db)
    return [
        _build_project_response(p, stats_map.get(p.project_id, _empty_activity_stats()))
        for p in projects
    ]

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
    return _build_project_response(project, _empty_activity_stats())

@router.get("/projects/{project_id}", response_model=ProjectResponse)
def get_project_by_id(project_id: str, db: Session = Depends(get_db)):
    """Fetch a single project by ID."""
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID '{project_id}' not found."
        )
    stats_map = _load_project_activity_stats(db, [project.project_id])
    return _build_project_response(project, stats_map.get(project.project_id, _empty_activity_stats()))

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
        importer.import_excel_baseline(tmp_path, target_project_id=project_id)
        activities_count = db.query(ScheduleActivity).filter(ScheduleActivity.project_id == project_id).count()
        return {
            "project_id": project_id,
            "filename": file.filename,
            "status": "IMPORTED",
            "activities_imported": activities_count,
            "message": "Baseline schedule imported successfully."
        }
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
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
