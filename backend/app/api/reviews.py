from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.schemas.review import HumanReviewRequest, HumanReviewResponse
from backend.app.services.human_review_service import process_human_review_decision

router = APIRouter(tags=["Human Planner Review"])

@router.post("/reviews/{event_id}/decision", response_model=HumanReviewResponse, status_code=status.HTTP_200_OK)
def submit_human_review_decision(event_id: str, payload: HumanReviewRequest, db: Session = Depends(get_db)):
    """
    Submits a human planner review decision for an event requiring review or override.
    Supports decision choices: ACCEPT, SWITCH, REJECT, UNPLANNED.
    Invokes state validation, atomic schedule progress updates, and audit logging when accepted/switched.
    """
    try:
        res = process_human_review_decision(
            event_id=event_id,
            decision_type=payload.decision,
            selected_activity_id=payload.selected_activity_id,
            reason=payload.reason,
            db=db
        )
        return res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing human review decision: {str(e)}"
        )
