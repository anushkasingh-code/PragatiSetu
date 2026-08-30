from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.db.database import Base

class MatchCandidate(Base):
    __tablename__ = "match_candidates"

    candidate_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    event_id: Mapped[str] = mapped_column(String(50), ForeignKey("extracted_events.event_id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id: Mapped[str] = mapped_column(String(50), ForeignKey("schedule_activities.activity_id", ondelete="CASCADE"), nullable=False, index=True)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    identifier_score: Mapped[float] = mapped_column(Float, nullable=False)
    discipline_score: Mapped[float] = mapped_column(Float, nullable=False)
    location_score: Mapped[float] = mapped_column(Float, nullable=False)
    action_score: Mapped[float] = mapped_column(Float, nullable=False)
    fuzzy_score: Mapped[float] = mapped_column(Float, nullable=False)
    semantic_score: Mapped[float] = mapped_column(Float, nullable=False)
    temporal_score: Mapped[float] = mapped_column(Float, nullable=False)
    dependency_score: Mapped[float] = mapped_column(Float, nullable=False)
    top_2_margin: Mapped[float | None] = mapped_column(Float, nullable=True)
    matcher_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("ExtractedEvent", back_populates="candidates")
    activity = relationship("ScheduleActivity")
