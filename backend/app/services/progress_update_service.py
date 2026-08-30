import datetime
from typing import Tuple, List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.activity import ScheduleActivity
from backend.app.db.models.decision import MatchDecision
from backend.app.db.models.audit import AuditRecord
from backend.app.services.state_validator import (
    validate_state_transition,
    validate_date_ordering,
    validate_percentage,
    check_dependency_warnings
)
from backend.app.services.conflict_service import detect_schedule_conflicts
from backend.app.services.audit_service import build_schedule_state_snapshot, record_schedule_audit

class ProgressUpdateService:
    def __init__(self, db: Session):
        self.db = db

    def apply_event_progress(self, event_id: str) -> Dict[str, Any]:
        event = self.db.query(ExtractedEvent).filter(ExtractedEvent.event_id == event_id).first()
        if not event:
            raise ValueError(f"ExtractedEvent with ID '{event_id}' not found.")

        # Check idempotency: If an AuditRecord already exists for this event_id, return existing result without duplicate audit
        existing_audit = self.db.query(AuditRecord).filter(AuditRecord.event_id == event_id).first()
        if existing_audit:
            decision = self.db.query(MatchDecision).filter(MatchDecision.event_id == event_id).first()
            activity = self.db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == existing_audit.activity_id).first() if existing_audit.activity_id else None
            return {
                "event_id": event.event_id,
                "activity_id": activity.activity_id if activity else None,
                "decision": decision.decision if decision else "AUTO_LINK",
                "applied": True,
                "already_applied": True,
                "status": activity.status if activity else None,
                "percent_complete": activity.percent_complete if activity else None,
                "actual_start": str(activity.actual_start) if activity and activity.actual_start else None,
                "actual_finish": str(activity.actual_finish) if activity and activity.actual_finish else None,
                "warnings": [],
                "conflicts": [],
                "audit_id": existing_audit.audit_id
            }

        decision = self.db.query(MatchDecision).filter(MatchDecision.event_id == event_id).first()
        if not decision:
            raise ValueError(f"MatchDecision for event ID '{event_id}' not found. Evaluate decision first.")

        # Safety Gate: Only AUTO_LINK (or approved decision) is eligible for automatic schedule application
        if decision.decision != "AUTO_LINK":
            return {
                "event_id": event.event_id,
                "activity_id": decision.top_activity_id,
                "decision": decision.decision,
                "applied": False,
                "already_applied": False,
                "reason": f"Decision state '{decision.decision}' is not eligible for automatic schedule update.",
                "warnings": [],
                "conflicts": [],
                "audit_id": None
            }

        if not decision.top_activity_id:
            return {
                "event_id": event.event_id,
                "activity_id": None,
                "decision": decision.decision,
                "applied": False,
                "already_applied": False,
                "reason": "No target baseline activity linked to decision.",
                "warnings": [],
                "conflicts": [],
                "audit_id": None
            }

        activity = self.db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == decision.top_activity_id).first()
        if not activity:
            raise ValueError(f"ScheduleActivity with ID '{decision.top_activity_id}' not found.")

        # Capture BEFORE snapshot
        previous_value = build_schedule_state_snapshot(activity)

        # Compute proposed status and actual dates
        evt_status = (event.status or "").upper()
        evt_pct = event.percent_complete
        evt_date = event.event_date

        proposed_status = activity.status
        proposed_percent = activity.percent_complete
        proposed_start = activity.actual_start
        proposed_finish = activity.actual_finish

        if evt_status == "COMPLETED" or (evt_pct is not None and evt_pct >= 100.0):
            proposed_status = "COMPLETED"
            proposed_percent = 100.0
            if evt_date:
                proposed_finish = evt_date
            if proposed_start is None and evt_date:
                proposed_start = evt_date
        elif evt_status == "STARTED":
            proposed_status = "STARTED" if (evt_pct is None or evt_pct == 0) else "IN_PROGRESS"
            if evt_pct is not None:
                proposed_percent = evt_pct
            if proposed_start is None and evt_date:
                proposed_start = evt_date
        elif evt_status == "IN_PROGRESS":
            proposed_status = "IN_PROGRESS"
            if evt_pct is not None:
                proposed_percent = evt_pct
            if proposed_start is None and evt_date:
                proposed_start = evt_date
        elif evt_status == "REWORK":
            proposed_status = "REWORK"
            if evt_pct is not None:
                proposed_percent = evt_pct

        # Check dependency warnings
        warnings = check_dependency_warnings(activity, self.db)

        # Detect conflicts
        conflicts = detect_schedule_conflicts(
            activity=activity,
            proposed_status=proposed_status,
            proposed_percent=proposed_percent,
            proposed_start=proposed_start,
            proposed_finish=proposed_finish
        )

        # If conflicts exist, route to CONFLICT_REVIEW and do NOT mutate schedule
        if conflicts:
            # Update decision record to CONFLICT_REVIEW so it appears in review queue
            decision.decision = "CONFLICT_REVIEW"
            conflict_reason = "; ".join([c["message"] for c in conflicts])
            existing_reasons = decision.reasons or []
            existing_reasons.append(f"CONFLICT_REVIEW: {conflict_reason}")
            decision.reasons = existing_reasons
            self.db.commit()
            return {
                "event_id": event.event_id,
                "activity_id": activity.activity_id,
                "decision": "CONFLICT_REVIEW",
                "applied": False,
                "already_applied": False,
                "status": activity.status,
                "percent_complete": activity.percent_complete,
                "actual_start": str(activity.actual_start) if activity.actual_start else None,
                "actual_finish": str(activity.actual_finish) if activity.actual_finish else None,
                "warnings": [w["message"] for w in warnings],
                "conflicts": [c["message"] for c in conflicts],
                "audit_id": None
            }

        # ATOMIC DATABASE TRANSACTION
        try:
            # 1. Update ScheduleActivity actuals (PLANNED DATES ARE NEVER TOUCHED)
            activity.status = proposed_status
            if proposed_percent is not None:
                activity.percent_complete = proposed_percent
            if proposed_start is not None and activity.actual_start is None:
                activity.actual_start = proposed_start
            if proposed_finish is not None:
                activity.actual_finish = proposed_finish

            # Capture AFTER snapshot
            new_value = build_schedule_state_snapshot(activity)

            # 2. Record AuditRecord
            audit = record_schedule_audit(
                db=self.db,
                project_id=activity.project_id,
                activity_id=activity.activity_id,
                event_id=event.event_id,
                report_id=event.report_id,
                previous_value=previous_value,
                new_value=new_value,
                system_decision=decision.decision,
                confidence=decision.match_confidence,
                reason=f"Applied progress update from event '{event.event_id}'. Status: {proposed_status}, Progress: {activity.percent_complete}%.",
                matcher_version=decision.matcher_version,
                scoring_policy_version=decision.scoring_policy_version
            )

            # Commit entire atomic transaction
            self.db.commit()
            self.db.refresh(activity)
            self.db.refresh(audit)

            return {
                "event_id": event.event_id,
                "activity_id": activity.activity_id,
                "decision": decision.decision,
                "applied": True,
                "already_applied": False,
                "status": activity.status,
                "percent_complete": activity.percent_complete,
                "actual_start": str(activity.actual_start) if activity.actual_start else None,
                "actual_finish": str(activity.actual_finish) if activity.actual_finish else None,
                "warnings": [w["message"] for w in warnings],
                "conflicts": [],
                "audit_id": audit.audit_id
            }

        except IntegrityError:
            # DB-level unique constraint on audit.event_id fired: a concurrent thread already
            # committed this exact event → roll back and report as already applied (BUG-002 fix)
            self.db.rollback()
            existing_audit = self.db.query(AuditRecord).filter(AuditRecord.event_id == event_id).first()
            refreshed_act = self.db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == decision.top_activity_id).first() if decision.top_activity_id else None
            return {
                "event_id": event.event_id,
                "activity_id": refreshed_act.activity_id if refreshed_act else None,
                "decision": decision.decision,
                "applied": True,
                "already_applied": True,
                "status": refreshed_act.status if refreshed_act else None,
                "percent_complete": refreshed_act.percent_complete if refreshed_act else None,
                "actual_start": str(refreshed_act.actual_start) if refreshed_act and refreshed_act.actual_start else None,
                "actual_finish": str(refreshed_act.actual_finish) if refreshed_act and refreshed_act.actual_finish else None,
                "warnings": [w["message"] for w in warnings],
                "conflicts": [],
                "audit_id": existing_audit.audit_id if existing_audit else None
            }

        except Exception as e:
            self.db.rollback()
            raise RuntimeError(f"Atomic transaction failed during schedule progress update: {str(e)}")

