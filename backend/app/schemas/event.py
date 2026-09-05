from datetime import date, datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.common import UtcDatetime

class ExtractedEventResponse(BaseModel):
    event_id: str
    report_id: str
    raw_text: str
    event_date: Optional[date] = None
    event_date_source: Optional[str] = None
    discipline: Optional[str] = None
    action: Optional[str] = None
    object: Optional[str] = None
    identifier: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    percent_complete: Optional[float] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    source_position: Optional[Dict[str, Any]] = None
    extraction_method: str = "RULE_BASED"
    extraction_version: str = "v1"
    created_at: UtcDatetime

    model_config = ConfigDict(from_attributes=True)

class ExtractionResultResponse(BaseModel):
    report_id: str
    processing_status: str
    event_count: int
    events: List[ExtractedEventResponse]
