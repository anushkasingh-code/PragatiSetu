import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.db.models.audit import AuditRecord

def build_schedule_state_snapshot(activity: Any) -> Dict[str, Any]:
    """Captures JSON snapshot of schedule activity actuals and status."""
    return {
        "status": activity.status,
        "percent_complete": activity.percent_complete,
        "actual_start": str(activity.actual_start) if activity.actual_start else None,
        "actual_finish": str(activity.actual_finish) if activity.actual_finish else None
    }

def record_schedule_audit(
    db: Session,
    project_id: str,
    activity_id: str,
    event_id: str,
    report_id: Optional[str],
    previous_value: Dict[str, Any],
    new_value: Dict[str, Any],
    system_decision: str,
    confidence: float,
    reason: str,
    matcher_version: str = "v1",
    scoring_policy_version: str = "v1"
) -> AuditRecord:
    """Creates immutable AuditRecord entry with before/after state snapshots."""
    audit_id = f"AUD-{uuid.uuid4().hex[:8].upper()}"
    audit = AuditRecord(
        audit_id=audit_id,
        project_id=project_id,
        activity_id=activity_id,
        event_id=event_id,
        report_id=report_id,
        previous_value=previous_value,
        new_value=new_value,
        system_decision=system_decision,
        confidence=confidence,
        reason=reason,
        matcher_version=matcher_version,
        scoring_policy_version=scoring_policy_version
    )
    db.add(audit)
    return audit
