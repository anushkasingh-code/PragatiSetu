import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.db.database import Base
from typing import Any

class DecisionEnum(str, enum.Enum):
    AUTO_LINK = "AUTO_LINK"
    AUTO_LINK_ELIGIBLE = "AUTO_LINK"  # Alias accepted by architecture docs
    HUMAN_REVIEW = "HUMAN_REVIEW"
    UNPLANNED_REVIEW = "UNPLANNED_REVIEW"
    CONFLICT_REVIEW = "CONFLICT_REVIEW"
    IGNORE = "IGNORE"

class MatchDecision(Base):
    __tablename__ = "match_decisions"

    decision_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    event_id: Mapped[str] = mapped_column(String(50), ForeignKey("extracted_events.event_id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    top_activity_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("schedule_activities.activity_id", ondelete="SET NULL"), nullable=True, index=True)
    match_confidence: Mapped[float] = mapped_column(Float, nullable=False)
    evidence_completeness: Mapped[float] = mapped_column(Float, nullable=False)
    top_2_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    decision: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    reasons: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    missing_evidence: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    matcher_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    scoring_policy_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("ExtractedEvent")
    top_activity = relationship("ScheduleActivity")
