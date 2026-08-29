from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.db.models.report import SourceReport
from backend.app.db.models.event import ExtractedEvent
from backend.app.schemas.event import ExtractionResultResponse, ExtractedEventResponse
from backend.app.schemas.decision import DecisionExplanationResponse
from backend.app.services.event_extraction_service import EventExtractionService
from backend.app.services.decision_service import DecisionService

router = APIRouter(tags=["Event Extraction & Matching"])

@router.post("/reports/{report_id}/extract-events", response_model=ExtractionResultResponse, status_code=status.HTTP_200_OK)
@router.post("/reports/{report_id}/extract", response_model=ExtractionResultResponse, status_code=status.HTTP_200_OK)
def extract_events_from_report(report_id: str, db: Session = Depends(get_db)):
    """
    Triggers deterministic rule-based event extraction on a validated report.
    Splits multi-event content, extracts structured fields, preserves raw text provenance, and stores ExtractedEvent records.
    Idempotent: Returns existing extracted events if already processed.
    """
    report = db.query(SourceReport).filter(SourceReport.report_id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found."
        )

    service = EventExtractionService(db)
    try:
        updated_report, events = service.extract_events_from_report(report_id)
        return {
            "report_id": updated_report.report_id,
            "processing_status": updated_report.processing_status,
            "event_count": len(events),
            "events": events
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error extracting events from report: {str(e)}"
        )

@router.get("/reports/{report_id}/events", response_model=List[ExtractedEventResponse])
def get_report_events(report_id: str, db: Session = Depends(get_db)):
    """Retrieves all extracted events associated with a report."""
    report = db.query(SourceReport).filter(SourceReport.report_id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID '{report_id}' not found."
        )
    events = db.query(ExtractedEvent).filter(ExtractedEvent.report_id == report_id).all()
    return events

@router.post("/events/{event_id}/match", response_model=DecisionExplanationResponse, status_code=status.HTTP_200_OK)
def match_event_to_candidates(event_id: str, db: Session = Depends(get_db)):
    """
    Triggers candidate generation, 8-component evidence scoring, and 85/70/12 safety decision policy evaluation for an event.
    Routes event into AUTO_LINK, HUMAN_REVIEW, UNPLANNED_REVIEW, or IGNORE.
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
            detail=f"Error evaluating event match decision: {str(e)}"
        )
