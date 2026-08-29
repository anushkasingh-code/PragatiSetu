from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.schemas.timeline import ProjectTimelineResponse
from backend.app.services.timeline_service import get_project_timeline_data

router = APIRouter(tags=["Project Timeline / Gantt Data"])

@router.get("/projects/{project_id}/timeline", response_model=ProjectTimelineResponse)
def get_project_timeline(project_id: str, db: Session = Depends(get_db)):
    """
    Retrieves baseline schedule activities formatted for Gantt timeline visualization.
    Exposes planned_start, planned_finish, actual_start, actual_finish, percent_complete, and status separately.
    PLANNED DATES ARE IMMUTABLE and preserved side-by-side with actual progress.
    """
    try:
        data = get_project_timeline_data(project_id, db)
        return data
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving project timeline: {str(e)}"
        )
