from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.candidate import MatchCandidate
from backend.app.schemas.candidate import CandidateListResponse, NormalizedEventResponse, CandidateScoreDetail
from backend.app.services.candidate_generator_service import CandidateGeneratorService

router = APIRouter(tags=["Candidate Generation & Normalization"])

@router.post("/events/{event_id}/normalize", response_model=NormalizedEventResponse, status_code=status.HTTP_200_OK)
def normalize_extracted_event(event_id: str, db: Session = Depends(get_db)):
    """
    Normalizes extracted event fields (identifiers, terminology, location) using deterministic dictionary mapping.
    Preserves raw extracted source values.
    """
    service = CandidateGeneratorService(db)
    try:
        event = service.normalize_event(event_id)
        return {
            "event_id": event.event_id,
            "raw_identifier": event.identifier,
            "normalized_identifier": event.normalized_identifier,
            "raw_action": event.action,
            "normalized_action": event.normalized_action,
            "raw_object": event.object,
            "normalized_object": event.normalized_object,
            "raw_location": event.location,
            "normalized_location": event.normalized_location,
            "normalization_version": event.normalization_version or "v1"
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error normalizing event: {str(e)}"
        )

@router.post("/events/{event_id}/candidates", response_model=CandidateListResponse, status_code=status.HTTP_200_OK)
def generate_event_candidates(event_id: str, top_n: int = Query(5, ge=1, le=20), db: Session = Depends(get_db)):
    """
    Generates a ranked shortlist of baseline ScheduleActivity candidates for an extracted event.
    Computes 8 independent component evidence scores (identifier, discipline, location, action, fuzzy, semantic, temporal, dependency)
    and overall weighted heuristic score.
    Calculates top-2 margin and persists MatchCandidate records.
    """
    service = CandidateGeneratorService(db)
    try:
        event, candidates, top_2_margin = service.generate_candidates_for_event(event_id, top_n=top_n)
        return {
            "event_id": event.event_id,
            "normalized_identifier": event.normalized_identifier,
            "normalized_action": event.normalized_action,
            "normalized_location": event.normalized_location,
            "top_2_margin": top_2_margin,
            "candidate_count": len(candidates),
            "candidates": candidates
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating candidates: {str(e)}"
        )

@router.get("/events/{event_id}/candidates", response_model=CandidateListResponse)
def get_event_candidates(event_id: str, db: Session = Depends(get_db)):
    """Retrieves persisted candidate results for an event."""
    event = db.query(ExtractedEvent).filter(ExtractedEvent.event_id == event_id).first()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ExtractedEvent with ID '{event_id}' not found."
        )

    candidates = db.query(MatchCandidate).filter(MatchCandidate.event_id == event_id).order_by(MatchCandidate.rank.asc()).all()
    
    top_2_margin = None
    if len(candidates) >= 2:
        top_2_margin = round(candidates[0].overall_score - candidates[1].overall_score, 2)

    return {
        "event_id": event.event_id,
        "normalized_identifier": event.normalized_identifier,
        "normalized_action": event.normalized_action,
        "normalized_location": event.normalized_location,
        "top_2_margin": top_2_margin,
        "candidate_count": len(candidates),
        "candidates": candidates
    }
