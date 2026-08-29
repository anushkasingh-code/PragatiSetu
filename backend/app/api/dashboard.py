from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.schemas.dashboard import ProjectDashboardResponse
from backend.app.services.dashboard_service import get_project_dashboard_summary

router = APIRouter(tags=["Project Dashboard"])

@router.get("/projects/{project_id}/dashboard", response_model=ProjectDashboardResponse)
def get_project_dashboard(project_id: str, db: Session = Depends(get_db)):
    """
    Retrieves real aggregated database counts for a project.
    Includes activity status metrics, reports received, events extracted, safety decisions, and conflicts.
    """
    try:
        summary = get_project_dashboard_summary(project_id, db)
        return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dashboard metrics: {str(e)}"
        )
