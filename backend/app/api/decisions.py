from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.decision import MatchDecision
from backend.app.schemas.decision import DecisionExplanationResponse, MatchDecisionResponse
from backend.app.services.decision_service import DecisionService

router = APIRouter(tags=["Safety Decision Routing"])

@router.post("/events/{event_id}/decision", response_model=DecisionExplanationResponse, status_code=status.HTTP_200_OK)
def evaluate_and_create_event_decision(event_id: str, db: Session = Depends(get_db)):
    """
    Evaluates safety decision policy thresholds (85/70/12) for an extracted event.
    Routes event into AUTO_LINK, HUMAN_REVIEW, UNPLANNED_REVIEW, or IGNORE.
    Persists MatchDecision record and returns structured judge-facing explanation.
    CRITICAL SAFETY GUARANTEE: Does NOT modify ScheduleActivity objects or schedule actuals.
    """
    service = DecisionService(db)
    try:
        event, decision = service.make_decision_for_event(event_id)
        return {
            "event_id": event.event_id,
            "decision": decision.decision,
            "top_activity_id": decision.top_activity_id,
            "match_confidence": decision.match_confidence,
            "evidence_completeness": decision.evidence_completeness,
            "top_2_margin": decision.top_2_margin,
            "reasons": decision.reasons or [],
            "missing_evidence": decision.missing_evidence or [],
            "matcher_version": decision.matcher_version,
            "scoring_policy_version": decision.scoring_policy_version
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating event decision: {str(e)}"
        )

@router.get("/events/{event_id}/decision", response_model=MatchDecisionResponse)
def get_event_decision(event_id: str, db: Session = Depends(get_db)):
    """Retrieves persisted MatchDecision record for an event."""
    event = db.query(ExtractedEvent).filter(ExtractedEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ExtractedEvent with ID '{event_id}' not found."
        )

    decision = db.query(MatchDecision).filter(MatchDecision.event_id == event_id).first()
    if not decision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"MatchDecision for event ID '{event_id}' not found. Call POST /events/{event_id}/decision first."
        )

    return decision
