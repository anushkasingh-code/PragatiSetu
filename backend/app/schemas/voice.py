from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field
from backend.app.schemas.event import ExtractedEventResponse
from backend.app.schemas.common import UtcDatetime

class TranscriptionResponse(BaseModel):
    transcription_id: str
    filename: str
    transcript: Optional[str] = None
    language: Optional[str] = "en"
    duration_seconds: Optional[float] = None
    model_name: str
    processing_time_ms: Optional[int] = 0
    status: str
    error_message: Optional[str] = None
    created_at: UtcDatetime

    model_config = ConfigDict(from_attributes=True)

class TranscriptUpdateRequest(BaseModel):
    transcript: str = Field(..., min_length=1, description="Corrected transcript text from human planner")

class VoiceProcessRequest(BaseModel):
    transcription_id: str
    project_id: Optional[str] = None

class VoiceProcessResponse(BaseModel):
    transcription_id: str
    transcript: str
    report_id: str
    processing_status: str
    event_count: int
    events: List[ExtractedEventResponse]

    model_config = ConfigDict(from_attributes=True)
