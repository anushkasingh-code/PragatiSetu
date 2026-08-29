from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class WBSNodeBase(BaseModel):
    wbs_id: str
    project_id: str
    parent_wbs_id: Optional[str] = None
    level: int
    name: str

class WBSNodeCreate(WBSNodeBase):
    pass

class WBSNodeResponse(WBSNodeBase):
    model_config = ConfigDict(from_attributes=True)

class WBSTreeNode(WBSNodeResponse):
    children: List["WBSTreeNode"] = []
    model_config = ConfigDict(from_attributes=True)

WBSTreeNode.model_rebuild()
