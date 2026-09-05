from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from backend.app.schemas.common import UtcDatetime

class ValidationErrorItem(BaseModel):
    code: str
    message: str

class ValidationDetail(BaseModel):
    valid: bool
    errors: List[ValidationErrorItem] = []
    warnings: List[str] = []

class ReportUploadResponse(BaseModel):
    report_id: str
    project_id: str
    filename: str
    source_type: str
    report_date: str
    discipline: Optional[str] = None
    processing_status: str
    file_hash: str
    duplicate: bool = False
    validation: ValidationDetail

class ReportResponse(BaseModel):
    report_id: str
    project_id: str
    filename: str
    source_type: str
    report_date: date
    discipline: Optional[str] = None
    file_hash: str
    file_size: int
    processing_status: str
    rejection_reason: Optional[str] = None
    created_at: UtcDatetime

    model_config = ConfigDict(from_attributes=True)
