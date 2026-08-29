from datetime import datetime, timezone
from enum import Enum
from sqlalchemy import Column, String, Text, Date, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    EVENTS_EXTRACTED = "EVENTS_EXTRACTED"
    PROCESSED = "PROCESSED"

class SourceReport(Base):
    __tablename__ = "source_reports"

    report_id = Column(String(50), primary_key=True, index=True)
    project_id = Column(String(50), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    source_type = Column(String(20), nullable=False)
    report_date = Column(Date, nullable=False)
    discipline = Column(String(100), nullable=True)
    raw_content = Column(Text, nullable=True)
    file_hash = Column(String(64), nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    stored_path = Column(String(500), nullable=False)
    processing_status = Column(String(50), default=ProcessingStatus.VALIDATED.value, nullable=False)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", back_populates="reports")
    events = relationship("ExtractedEvent", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "file_hash", name="uq_project_file_hash"),
    )
