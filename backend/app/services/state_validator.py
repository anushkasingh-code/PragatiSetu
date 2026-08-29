import datetime
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from backend.app.db.models.activity import ScheduleActivity

VALID_TRANSITIONS = {
    "NOT_STARTED": ["NOT_STARTED", "STARTED", "IN_PROGRESS", "COMPLETED"],
    "STARTED": ["STARTED", "IN_PROGRESS", "COMPLETED"],
    "IN_PROGRESS": ["IN_PROGRESS", "COMPLETED"],
    "COMPLETED": ["COMPLETED", "REWORK"],
    "REWORK": ["REWORK", "IN_PROGRESS", "COMPLETED"]
}

def validate_state_transition(current_status: str, target_status: str) -> bool:
    """Validates if status transition from current_status to target_status is permitted."""
    allowed = VALID_TRANSITIONS.get(current_status, [current_status])
    return target_status in allowed

def validate_date_ordering(actual_start: Optional[datetime.date], actual_finish: Optional[datetime.date]) -> Tuple[bool, Optional[str]]:
    """Validates actual_finish >= actual_start."""
    if actual_start and actual_finish and actual_finish < actual_start:
        return False, "INVALID_DATE_ORDER: actual_finish date cannot be earlier than actual_start date."
    return True, None

def validate_percentage(percentage: Optional[float]) -> Tuple[bool, Optional[str]]:
    """Validates reported progress percentage is within range 0.0 to 100.0."""
    if percentage is not None:
        if percentage < 0.0 or percentage > 100.0:
            return False, f"INVALID_PERCENTAGE: Reported percentage {percentage}% is out of valid range (0.0 - 100.0%)."
    return True, None

def check_dependency_warnings(activity: ScheduleActivity, db: Session) -> List[Dict[str, str]]:
    """Checks predecessor status and returns dependency warnings if successor finishes before predecessor."""
    warnings = []
    if activity.predecessor_activity_id:
        pred = db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == activity.predecessor_activity_id).first()
        if pred and pred.status != "COMPLETED":
            warnings.append({
                "type": "DEPENDENCY_WARNING",
                "message": f"Successor activity '{activity.activity_id}' reported complete/in-progress before mandatory predecessor '{pred.activity_id}' reached completion."
            })
    return warnings
