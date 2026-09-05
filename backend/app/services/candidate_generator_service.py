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
from backend.app.services.embedding_service import precompute_schedule_embeddings, is_embedding_model_degraded
from backend.app.services.candidate_scorer import compute_all_candidate_scores
from backend.app.services.ai.vector_retriever import search_schedule_activities

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
        activities_to_score = []
        
        # Construct semantic query
        query_text = f"{event.normalized_action or ''} {event.normalized_object or ''} {event.normalized_location or ''}".strip()
        if not query_text:
            query_text = event.raw_text or ""
            
        vector_results = search_schedule_activities(
            project_id=project_id,
            query=query_text,
            top_k=max(10, top_n * 2)
        )
        
        if vector_results and not is_embedding_model_degraded():
            # We got semantic candidates and model is healthy. Retrieve these specific activities.
            vector_act_ids = [res.activity_id for res in vector_results]
            
            # Also ALWAYS include exact identifier matches if an identifier exists, to prevent semantic misses on IDs
            if event.normalized_identifier:
                from sqlalchemy import or_
                identifier_matches = self.db.query(ScheduleActivity).filter(
                    ScheduleActivity.project_id == project_id,
                    or_(
                        ScheduleActivity.activity_id == event.normalized_identifier,
                        ScheduleActivity.equipment_or_line_id == event.normalized_identifier
                    )
                ).all()
                for match in identifier_matches:
                    if match.activity_id not in vector_act_ids:
                        vector_act_ids.append(match.activity_id)
            
            activities_to_score = self.db.query(ScheduleActivity).filter(
                ScheduleActivity.project_id == project_id,
                ScheduleActivity.activity_id.in_(vector_act_ids)
            ).all()
        else:
            # Fallback: if vector search fails or returns empty, score all (existing deterministic behavior)
            activities_to_score = self.db.query(ScheduleActivity).filter(ScheduleActivity.project_id == project_id).all()

        if not activities_to_score:
            return event, [], None

        candidate_scores_list = []
        for act in activities_to_score:
            scores = compute_all_candidate_scores(event, act)
            
            # If the candidate came from vector search, we can inject the vector similarity score
            # However, compute_all_candidate_scores already computes semantic_score using SentenceTransformers.
            # We will rely on compute_all_candidate_scores for the authoritative score.
            
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
