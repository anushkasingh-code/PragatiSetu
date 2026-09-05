from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.common import UtcDatetime

class ApplyProgressResponse(BaseModel):
    event_id: str
    activity_id: Optional[str] = None
    decision: str
    applied: bool
    already_applied: bool = False
    reason: Optional[str] = None
    status: Optional[str] = None
    percent_complete: Optional[float] = None
    actual_start: Optional[str] = None
    actual_finish: Optional[str] = None
    warnings: List[str] = []
    conflicts: List[str] = []
    audit_id: Optional[str] = None

class AuditRecordResponse(BaseModel):
    audit_id: str
    timestamp: UtcDatetime
    project_id: str
    activity_id: str
    event_id: str
    report_id: Optional[str] = None
    previous_value: Dict[str, Any]
    new_value: Dict[str, Any]
    system_decision: str
    confidence: float
    reviewer: str
    reason: str
    matcher_version: str = "v1"
    scoring_policy_version: str = "v1"

    model_config = ConfigDict(from_attributes=True)
