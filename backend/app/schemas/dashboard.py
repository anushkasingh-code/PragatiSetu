from typing import Optional
from pydantic import BaseModel, ConfigDict

class ProjectDashboardResponse(BaseModel):
    project_id: str
    project_name: str
    total_activities: int
    completed_activities: int
    in_progress_activities: int
    started_activities: int
    not_started_activities: int
    progress_percentage: float = 0.0
    total_reports: int
    total_events: int
    auto_linked_events: int
    human_review_events: int
    unplanned_events: int
    conflict_events: int
    ignore_events: int = 0
    applied_events: int = 0
    duplicate_reports: int

    model_config = ConfigDict(from_attributes=True)
