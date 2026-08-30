import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Text, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.db.database import Base
from typing import Any

class ActivityStatusEnum(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REWORK = "REWORK"

class AuditRecord(Base):
    __tablename__ = "audit_records"

    audit_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    activity_id: Mapped[str] = mapped_column(String(50), ForeignKey("schedule_activities.activity_id", ondelete="CASCADE"), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(50), ForeignKey("extracted_events.event_id", ondelete="CASCADE"), nullable=False, index=True)
    report_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("source_reports.report_id", ondelete="SET NULL"), nullable=True)
    previous_value: Mapped[Any] = mapped_column(JSON, nullable=False)
    new_value: Mapped[Any] = mapped_column(JSON, nullable=False)
    system_decision: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reviewer: Mapped[str] = mapped_column(String(100), default="SYSTEM_AUTO_LINK", nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    matcher_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    scoring_policy_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)

    project = relationship("Project")
    activity = relationship("ScheduleActivity")
    event = relationship("ExtractedEvent")
    report = relationship("SourceReport")
