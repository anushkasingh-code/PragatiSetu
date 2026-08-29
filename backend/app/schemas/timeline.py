from datetime import date
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ActivityTimelineItem(BaseModel):
    activity_id: str
    wbs_id: str
    discipline: str
    description: str
    location: Optional[str] = None
    equipment_or_line_id: Optional[str] = None
    planned_start: date
    planned_finish: date
    actual_start: Optional[date] = None
    actual_finish: Optional[date] = None
    percent_complete: float
    status: str
    predecessor_activity_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class ProjectTimelineResponse(BaseModel):
    project_id: str
    project_name: str
    total_activities: int
    activities: List[ActivityTimelineItem]

    model_config = ConfigDict(from_attributes=True)
