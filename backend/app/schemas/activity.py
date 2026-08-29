from datetime import date
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, field_validator

class ActivityBase(BaseModel):
    activity_id: str
    project_id: str
    wbs_id: Optional[str] = None
    discipline: str
    description: str
    location: Optional[str] = None
    equipment_or_line_id: Optional[str] = None
    planned_start: date
    planned_finish: date
    actual_start: Optional[date] = None
    actual_finish: Optional[date] = None
    percent_complete: float = Field(default=0.0, ge=0.0, le=100.0)
    status: str = Field(default="NOT_STARTED")
    predecessor_activity_id: Optional[str] = None

    @field_validator("planned_finish")
    @classmethod
    def validate_planned_dates(cls, v, info):
        if "planned_start" in info.data and v < info.data["planned_start"]:
            raise ValueError("planned_finish cannot be earlier than planned_start")
        return v

class ActivityCreate(ActivityBase):
    pass

class ActivityResponse(ActivityBase):
    model_config = ConfigDict(from_attributes=True)
