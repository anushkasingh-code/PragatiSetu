import datetime
from typing import Optional, List, Dict, Any
from backend.app.db.models.activity import ScheduleActivity

def detect_schedule_conflicts(
    activity: ScheduleActivity,
    proposed_status: str,
    proposed_percent: Optional[float],
    proposed_start: Optional[datetime.date],
    proposed_finish: Optional[datetime.date]
) -> List[Dict[str, str]]:
    """
    Evaluates proposed updates against current persisted schedule state.
    Detects STATUS_CONFLICT, PERCENTAGE_CONFLICT, DATE_CONFLICT, and INVALID_DATE_ORDER.
    """
    conflicts = []

    # 1. Invalid date order check
    eff_start = proposed_start or activity.actual_start
    eff_finish = proposed_finish or activity.actual_finish
    if eff_start and eff_finish and eff_finish < eff_start:
        conflicts.append({
            "type": "INVALID_DATE_ORDER",
            "message": f"Proposed finish date ({eff_finish}) is earlier than start date ({eff_start})."
        })

    # 2. Percentage bounds check
    if proposed_percent is not None and (proposed_percent < 0.0 or proposed_percent > 100.0):
        conflicts.append({
            "type": "INVALID_PERCENTAGE",
            "message": f"Proposed percentage ({proposed_percent}%) is outside valid 0-100% range."
        })

    # 3. Status conflict check: Completed activity moved back to IN_PROGRESS or STARTED (without REWORK)
    if activity.status == "COMPLETED" and proposed_status in ["STARTED", "IN_PROGRESS"]:
        conflicts.append({
            "type": "STATUS_CONFLICT",
            "message": f"Activity '{activity.activity_id}' is already COMPLETED (100%). Proposed status '{proposed_status}' conflicts with accepted state."
        })

    # 4. Backward percentage regression check
    if proposed_percent is not None and activity.percent_complete is not None:
        if proposed_percent < activity.percent_complete and proposed_status != "REWORK":
            conflicts.append({
                "type": "PERCENTAGE_CONFLICT",
                "message": f"Proposed percentage ({proposed_percent}%) is less than current accepted percentage ({activity.percent_complete}%)."
            })

    # 5. Date regression check
    if proposed_finish and activity.actual_finish and proposed_finish != activity.actual_finish:
        if activity.status == "COMPLETED" and proposed_finish < activity.actual_finish:
            conflicts.append({
                "type": "DATE_CONFLICT",
                "message": f"Proposed actual_finish ({proposed_finish}) contradicts existing actual_finish ({activity.actual_finish})."
            })

    return conflicts
