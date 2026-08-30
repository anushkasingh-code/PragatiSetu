from datetime import datetime, timezone, date
from enum import Enum
from sqlalchemy import Column, String, Text, Date, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.db.database import Base

class ProcessingStatus(str, Enum):
    PENDING = "PENDING"
    VALIDATED = "VALIDATED"
    REJECTED = "REJECTED"
    EVENTS_EXTRACTED = "EVENTS_EXTRACTED"
    PROCESSED = "PROCESSED"

class SourceReport(Base):
    __tablename__ = "source_reports"

    report_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    report_date: Mapped[date] = mapped_column(Date, nullable=False)
    discipline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    stored_path: Mapped[str] = mapped_column(String(500), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(50), default=ProcessingStatus.VALIDATED.value, nullable=False)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", back_populates="reports")
    events = relationship("ExtractedEvent", back_populates="report", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("project_id", "file_hash", name="uq_project_file_hash"),
    )
