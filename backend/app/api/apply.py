from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.db.models.activity import ScheduleActivity
from backend.app.db.models.audit import AuditRecord
from backend.app.schemas.audit import ApplyProgressResponse, AuditRecordResponse
from backend.app.services.progress_update_service import ProgressUpdateService

router = APIRouter(tags=["Schedule Progress & Audit Trail"])

@router.post("/events/{event_id}/apply", response_model=ApplyProgressResponse, status_code=status.HTTP_200_OK)
def apply_event_schedule_progress(event_id: str, db: Session = Depends(get_db)):
    """
    Applies an accepted MatchDecision (AUTO_LINK) to update baseline schedule actuals (actual_start, actual_finish, percent_complete, status).
    Creates an immutable AuditRecord containing BEFORE and AFTER JSON state snapshots.
    Executes in an ATOMIC DATABASE TRANSACTION with complete rollback on failure.
    CRITICAL BASELINE IMMUTABILITY GUARANTEE: Baseline planned schedule dates are NEVER modified or overwritten.
    Idempotent: Repeated applications for an already applied event safely return the existing result.
    """
    service = ProgressUpdateService(db)
    try:
        res = service.apply_event_progress(event_id)
        return res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error applying schedule progress update: {str(e)}"
        )

@router.get("/activities/{activity_id}/audit", response_model=List[AuditRecordResponse])
def get_activity_audit_trail(activity_id: str, db: Session = Depends(get_db)):
    """Retrieves immutable historical audit trail records for a baseline schedule activity."""
    act = db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == activity_id).first()
    if not act:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ScheduleActivity with ID '{activity_id}' not found."
        )

    records = db.query(AuditRecord).filter(AuditRecord.activity_id == activity_id).order_by(AuditRecord.timestamp.desc()).all()
    return records
