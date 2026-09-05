from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.common import UtcDatetime

class MatchDecisionResponse(BaseModel):
    decision_id: str
    event_id: str
    top_activity_id: Optional[str] = None
    match_confidence: float
    evidence_completeness: float
    top_2_margin: Optional[float] = None
    decision: str
    reasons: Optional[List[str]] = None
    missing_evidence: Optional[List[str]] = None
    matcher_version: str = "v1"
    scoring_policy_version: str = "v1"
    created_at: UtcDatetime

    model_config = ConfigDict(from_attributes=True)

class DecisionExplanationResponse(BaseModel):
    event_id: str
    decision: str
    top_activity_id: Optional[str] = None
    match_confidence: float
    evidence_completeness: float
    top_2_margin: Optional[float] = None
    reasons: List[str] = []
    missing_evidence: List[str] = []
    matcher_version: str = "v1"
    scoring_policy_version: str = "v1"

    model_config = ConfigDict(from_attributes=True)
