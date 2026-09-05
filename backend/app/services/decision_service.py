import uuid
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.candidate import MatchCandidate
from backend.app.db.models.decision import MatchDecision, DecisionEnum
from backend.app.services.candidate_generator_service import CandidateGeneratorService
from backend.app.services.evidence_service import calculate_evidence_completeness, derive_evidence_reasons
from backend.app.services.decision_policy import evaluate_decision_policy, SCORING_POLICY_VERSION

class DecisionService:
    def __init__(self, db: Session):
        self.db = db

    def make_decision_for_event(self, event_id: str) -> Tuple[ExtractedEvent, MatchDecision]:
        event = self.db.query(ExtractedEvent).filter(ExtractedEvent.event_id == event_id).first()
        if not event:
            raise ValueError(f"ExtractedEvent with ID '{event_id}' not found.")

        # Ensure candidates are generated
        candidates = self.db.query(MatchCandidate).filter(MatchCandidate.event_id == event_id).order_by(MatchCandidate.rank.asc()).all()
        if not candidates:
            gen = CandidateGeneratorService(self.db)
            event, candidates, _ = gen.generate_candidates_for_event(event_id)

        # 1. Calculate evidence completeness
        completeness_score, missing_fields = calculate_evidence_completeness(event)

        # 2. Calculate top-2 margin
        top_2_margin = None
        if len(candidates) >= 2:
            top_2_margin = round(candidates[0].overall_score - candidates[1].overall_score, 2)

        # 3. Evaluate safety decision policy
        decision_type, top_cand = evaluate_decision_policy(event, candidates, completeness_score, top_2_margin)

        # 4. Derive evidence-based reasons
        reasons = derive_evidence_reasons(event, top_cand)

        match_confidence = top_cand.overall_score if top_cand else 0.0
        top_activity_id = top_cand.activity_id if top_cand else None
        matcher_ver = top_cand.matcher_version if top_cand else "v1"

        # Idempotency check: Upsert existing decision
        existing_decision = self.db.query(MatchDecision).filter(MatchDecision.event_id == event_id).first()
        if existing_decision:
            # SAFETY GUARD (BUG-011): CONFLICT_REVIEW is a protected human review state.
            # Automatic re-evaluation MUST NOT overwrite it; only explicit human action may resolve it.
            if existing_decision.decision in ("CONFLICT_REVIEW", DecisionEnum.CONFLICT_REVIEW.value):
                return event, existing_decision

            existing_decision.top_activity_id = top_activity_id
            existing_decision.match_confidence = match_confidence
            existing_decision.evidence_completeness = completeness_score
            existing_decision.top_2_margin = top_2_margin
            existing_decision.decision = decision_type.value if hasattr(decision_type, "value") else str(decision_type)
            existing_decision.reasons = reasons
            existing_decision.missing_evidence = missing_fields
            existing_decision.matcher_version = matcher_ver
            existing_decision.scoring_policy_version = SCORING_POLICY_VERSION
            decision_record = existing_decision
        else:
            dec_id = f"DEC-{uuid.uuid4().hex[:12].upper()}"
            decision_record = MatchDecision(
                decision_id=dec_id,
                event_id=event_id,
                top_activity_id=top_activity_id,
                match_confidence=match_confidence,
                evidence_completeness=completeness_score,
                top_2_margin=top_2_margin,
                decision=decision_type.value if hasattr(decision_type, "value") else str(decision_type),
                reasons=reasons,
                missing_evidence=missing_fields,
                matcher_version=matcher_ver,
                scoring_policy_version=SCORING_POLICY_VERSION
            )
            self.db.add(decision_record)

        self.db.commit()
        self.db.refresh(decision_record)
        return event, decision_record
