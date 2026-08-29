import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Text, Enum
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class ActivityStatusEnum(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    STARTED = "STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REWORK = "REWORK"

class AuditRecord(Base):
    __tablename__ = "audit_records"

    audit_id = Column(String(50), primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    project_id = Column(String(50), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False)
    activity_id = Column(String(50), ForeignKey("schedule_activities.activity_id", ondelete="CASCADE"), nullable=False, index=True)
    event_id = Column(String(50), ForeignKey("extracted_events.event_id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(String(50), ForeignKey("source_reports.report_id", ondelete="SET NULL"), nullable=True)
    previous_value = Column(JSON, nullable=False)
    new_value = Column(JSON, nullable=False)
    system_decision = Column(String(50), nullable=False)
    confidence = Column(Float, nullable=False)
    reviewer = Column(String(100), default="SYSTEM_AUTO_LINK", nullable=False)
    reason = Column(Text, nullable=False)
    matcher_version = Column(String(20), default="v1", nullable=False)
    scoring_policy_version = Column(String(20), default="v1", nullable=False)

    project = relationship("Project")
    activity = relationship("ScheduleActivity")
    event = relationship("ExtractedEvent")
    report = relationship("SourceReport")
