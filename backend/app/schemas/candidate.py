from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class CandidateScoreDetail(BaseModel):
    candidate_id: str
    activity_id: str
    rank: int
    overall_score: float
    identifier_score: float
    discipline_score: float
    location_score: float
    action_score: float
    fuzzy_score: float
    semantic_score: float
    temporal_score: float
    dependency_score: float
    matcher_version: str = "v1"

    model_config = ConfigDict(from_attributes=True)

class CandidateListResponse(BaseModel):
    event_id: str
    normalized_identifier: Optional[str] = None
    normalized_action: Optional[str] = None
    normalized_location: Optional[str] = None
    top_2_margin: Optional[float] = None
    candidate_count: int
    candidates: List[CandidateScoreDetail]

class NormalizedEventResponse(BaseModel):
    event_id: str
    raw_identifier: Optional[str] = None
    normalized_identifier: Optional[str] = None
    raw_action: Optional[str] = None
    normalized_action: Optional[str] = None
    raw_object: Optional[str] = None
    normalized_object: Optional[str] = None
    raw_location: Optional[str] = None
    normalized_location: Optional[str] = None
    normalization_version: str = "v1"

    model_config = ConfigDict(from_attributes=True)
