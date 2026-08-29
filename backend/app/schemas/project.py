from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class ProjectBase(BaseModel):
    project_id: str
    name: str
    description: Optional[str] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectResponse(ProjectBase):
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
