from datetime import date, datetime
from typing import List, Dict, Any, Optional

class ValidationError(Exception):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

VALID_STATUSES = {"NOT_STARTED", "IN_PROGRESS", "COMPLETED", "ON_HOLD"}

def validate_date_range(planned_start: Any, planned_finish: Any) -> None:
    if isinstance(planned_start, str):
        planned_start = datetime.strptime(planned_start, "%Y-%m-%d").date()
    if isinstance(planned_finish, str):
        planned_finish = datetime.strptime(planned_finish, "%Y-%m-%d").date()

    if planned_finish < planned_start:
        raise ValidationError(
            f"Invalid date range: planned_finish ({planned_finish}) is earlier than planned_start ({planned_start})",
            {"planned_start": str(planned_start), "planned_finish": str(planned_finish)}
        )

def validate_percent_complete(percent_complete: float) -> None:
    if percent_complete < 0.0 or percent_complete > 100.0:
        raise ValidationError(
            f"Invalid percent_complete: {percent_complete}. Must be between 0.0 and 100.0.",
            {"percent_complete": percent_complete}
        )

def validate_status(status: str) -> None:
    if status not in VALID_STATUSES:
        raise ValidationError(
            f"Invalid status '{status}'. Must be one of {VALID_STATUSES}.",
            {"status": status, "valid_statuses": list(VALID_STATUSES)}
        )

def validate_duplicate_activity_ids(activity_ids: List[str]) -> None:
    seen = set()
    duplicates = set()
    for act_id in activity_ids:
        if act_id in seen:
            duplicates.add(act_id)
        else:
            seen.add(act_id)
    if duplicates:
        raise ValidationError(
            f"Duplicate activity IDs detected: {list(duplicates)}",
            {"duplicate_ids": list(duplicates)}
        )
