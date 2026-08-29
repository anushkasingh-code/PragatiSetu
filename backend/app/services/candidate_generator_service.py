import uuid
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.report import SourceReport
from backend.app.db.models.activity import ScheduleActivity
from backend.app.db.models.candidate import MatchCandidate
from backend.app.services.normalizer_service import (
    normalize_identifier,
    normalize_action,
    normalize_object,
    normalize_location
)
from backend.app.services.embedding_service import precompute_schedule_embeddings
from backend.app.services.candidate_scorer import compute_all_candidate_scores

class CandidateGeneratorService:
    def __init__(self, db: Session):
        self.db = db

    def normalize_event(self, event_id: str) -> ExtractedEvent:
        event = self.db.query(ExtractedEvent).filter(ExtractedEvent.event_id == event_id).first()
        if not event:
            raise ValueError(f"ExtractedEvent with ID '{event_id}' not found.")

        event.normalized_identifier = normalize_identifier(event.identifier)
        event.normalized_action = normalize_action(event.action)
        event.normalized_object = normalize_object(event.object)
        event.normalized_location = normalize_location(event.location)
        event.normalization_version = "v1"

        self.db.commit()
        self.db.refresh(event)
        return event

    def generate_candidates_for_event(self, event_id: str, top_n: int = 5) -> Tuple[ExtractedEvent, List[MatchCandidate], Optional[float]]:
        event = self.normalize_event(event_id)
        report = self.db.query(SourceReport).filter(SourceReport.report_id == event.report_id).first()
        if not report:
            raise ValueError(f"SourceReport with ID '{event.report_id}' not found.")

        project_id = report.project_id
        activities = self.db.query(ScheduleActivity).filter(ScheduleActivity.project_id == project_id).all()

        if not activities:
            return event, [], None

        # Precompute schedule activity embeddings in memory
        precompute_schedule_embeddings(activities)

        candidate_scores_list = []
        for act in activities:
            scores = compute_all_candidate_scores(event, act)
            candidate_scores_list.append((act, scores))

        # Sort descending by overall_score
        candidate_scores_list.sort(key=lambda x: x[1]["overall_score"], reverse=True)

        top_candidates_raw = candidate_scores_list[:max(1, top_n)]

        top_2_margin = None
        if len(top_candidates_raw) >= 2:
            top_2_margin = round(top_candidates_raw[0][1]["overall_score"] - top_candidates_raw[1][1]["overall_score"], 2)

        # Idempotency: Delete previous candidates for this event
        self.db.query(MatchCandidate).filter(MatchCandidate.event_id == event_id).delete()
        self.db.commit()

        persisted_candidates = []
        for rank, (act, scores) in enumerate(top_candidates_raw, start=1):
            cand_id = f"CAN-{uuid.uuid4().hex[:8].upper()}"
            cand = MatchCandidate(
                candidate_id=cand_id,
                event_id=event_id,
                activity_id=act.activity_id,
                rank=rank,
                overall_score=scores["overall_score"],
                identifier_score=scores["identifier_score"],
                discipline_score=scores["discipline_score"],
                location_score=scores["location_score"],
                action_score=scores["action_score"],
                fuzzy_score=scores["fuzzy_score"],
                semantic_score=scores["semantic_score"],
                temporal_score=scores["temporal_score"],
                dependency_score=scores["dependency_score"],
                top_2_margin=top_2_margin if rank == 1 else None,
                matcher_version="v1"
            )
            self.db.add(cand)
            persisted_candidates.append(cand)

        self.db.commit()
        for c in persisted_candidates:
            self.db.refresh(c)

        return event, persisted_candidates, top_2_margin
