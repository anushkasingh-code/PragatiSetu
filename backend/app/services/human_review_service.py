from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.activity import ScheduleActivity
from backend.app.db.models.decision import MatchDecision
from backend.app.services.decision_service import DecisionService
from backend.app.services.progress_update_service import ProgressUpdateService

VALID_REVIEW_DECISIONS = ["ACCEPT", "SWITCH", "REJECT", "UNPLANNED"]

def process_human_review_decision(
    event_id: str,
    decision_type: str,
    selected_activity_id: Optional[str],
    reason: Optional[str],
    db: Session
) -> Dict[str, Any]:
    norm_decision = (decision_type or "").upper().strip()
    if norm_decision not in VALID_REVIEW_DECISIONS:
        raise ValueError(f"Invalid review decision '{decision_type}'. Must be one of: {', '.join(VALID_REVIEW_DECISIONS)}.")

    event = db.query(ExtractedEvent).filter(ExtractedEvent.event_id == event_id).first()
    if not event:
        raise ValueError(f"ExtractedEvent with ID '{event_id}' not found.")

    decision = db.query(MatchDecision).filter(MatchDecision.event_id == event_id).first()
    if not decision:
        dec_service = DecisionService(db)
        _, decision = dec_service.make_decision_for_event(event_id)

    reviewer_note = f"Human Planner Review ({norm_decision}): {reason}" if reason else f"Human Planner Review ({norm_decision})"

    if norm_decision in ["ACCEPT", "SWITCH"]:
        target_act_id = selected_activity_id or decision.top_activity_id
        if not target_act_id:
            raise ValueError(f"Target activity ID must be specified for human review decision '{norm_decision}'.")

        activity = db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == target_act_id).first()
        if not activity:
            raise ValueError(f"ScheduleActivity with ID '{target_act_id}' not found.")

        decision.top_activity_id = target_act_id
        decision.decision = "AUTO_LINK"
        existing_reasons = decision.reasons or []
        existing_reasons.append(reviewer_note)
        decision.reasons = existing_reasons
        db.commit()

        # Invoke ProgressUpdateService to execute atomic schedule progress update and record audit record
        update_service = ProgressUpdateService(db)
        apply_res = update_service.apply_event_progress(event_id)

        return {
            "event_id": event_id,
            "decision": norm_decision,
            "selected_activity_id": target_act_id,
            "applied": apply_res.get("applied", False),
            "status": apply_res.get("status"),
            "percent_complete": apply_res.get("percent_complete"),
            "actual_start": apply_res.get("actual_start"),
            "actual_finish": apply_res.get("actual_finish"),
            "audit_id": apply_res.get("audit_id"),
            "message": f"Human review decision '{norm_decision}' successfully processed and applied to schedule."
        }

    else:  # REJECT or UNPLANNED
        decision.decision = "UNPLANNED" if norm_decision == "UNPLANNED" else "REJECT"
        decision.top_activity_id = None
        existing_reasons = list(decision.reasons or [])
        existing_reasons.append(reviewer_note)
        decision.reasons = existing_reasons
        db.commit()

        return {
            "event_id": event_id,
            "decision": norm_decision,
            "selected_activity_id": None,
            "applied": False,
            "status": None,
            "percent_complete": None,
            "actual_start": None,
            "actual_finish": None,
            "audit_id": None,
            "message": f"Human review decision '{norm_decision}' recorded. Schedule was not modified."
        }
