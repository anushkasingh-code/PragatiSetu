import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class DecisionEnum(str, enum.Enum):
    AUTO_LINK = "AUTO_LINK"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    UNPLANNED_REVIEW = "UNPLANNED_REVIEW"
    IGNORE = "IGNORE"

class MatchDecision(Base):
    __tablename__ = "match_decisions"

    decision_id = Column(String(50), primary_key=True, index=True)
    event_id = Column(String(50), ForeignKey("extracted_events.event_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    top_activity_id = Column(String(50), ForeignKey("schedule_activities.activity_id", ondelete="SET NULL"), nullable=True, index=True)
    match_confidence = Column(Float, nullable=False)
    evidence_completeness = Column(Float, nullable=False)
    top_2_margin = Column(Float, nullable=True)
    decision = Column(String(50), nullable=False, index=True)
    reasons = Column(JSON, nullable=True)
    missing_evidence = Column(JSON, nullable=True)
    matcher_version = Column(String(20), default="v1", nullable=False)
    scoring_policy_version = Column(String(20), default="v1", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("ExtractedEvent")
    top_activity = relationship("ScheduleActivity")
