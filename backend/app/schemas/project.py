from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.common import UtcDatetime

class ProjectBase(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    created_at: UtcDatetime
    status: Optional[str] = "Operational"
    progress_percentage: Optional[float] = 0.0
    total_activities: Optional[int] = 0
    completed_activities: Optional[int] = 0

    model_config = ConfigDict(from_attributes=True)
