import os
import shutil
import tempfile
from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.db.models.project import Project
from backend.app.db.models.wbs import WBSNode
from backend.app.db.models.activity import ScheduleActivity
from backend.app.schemas.project import ProjectCreate, ProjectResponse
from backend.app.schemas.wbs import WBSNodeResponse, WBSTreeNode
from backend.app.schemas.activity import ActivityResponse
from backend.app.services.baseline_importer import BaselineImporter

router = APIRouter(tags=["Projects & Activities"])

@router.get("/projects", response_model=List[ProjectResponse])
def get_projects(db: Session = Depends(get_db)):
    """Fetch all projects."""
    projects = db.query(Project).all()
    return projects

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

@router.post("/projects/{project_id}/schedule/upload", status_code=status.HTTP_200_OK)
async def upload_baseline_schedule(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Uploads an Excel baseline schedule file (.xlsx) and imports WBS nodes and Schedule Activities into the project database.
    """
    if not file.filename.endswith(".xlsx"):
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
