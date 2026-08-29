from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

class HumanReviewRequest(BaseModel):
    decision: str = Field(..., description="Decision choice: 'ACCEPT', 'SWITCH', 'REJECT', or 'UNPLANNED'")
    selected_activity_id: Optional[str] = Field(None, description="Target activity ID required when decision is 'ACCEPT' or 'SWITCH'")
    reason: Optional[str] = Field(None, description="Optional explanation reason from human planner")

class HumanReviewResponse(BaseModel):
    event_id: str
    decision: str
    selected_activity_id: Optional[str] = None
    applied: bool
    status: Optional[str] = None
    percent_complete: Optional[float] = None
    actual_start: Optional[str] = None
    actual_finish: Optional[str] = None
    audit_id: Optional[str] = None
    message: str

    model_config = ConfigDict(from_attributes=True)
