from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class MatchCandidate(Base):
    __tablename__ = "match_candidates"

    candidate_id = Column(String(50), primary_key=True, index=True)
    event_id = Column(String(50), ForeignKey("extracted_events.event_id", ondelete="CASCADE"), nullable=False, index=True)
    activity_id = Column(String(50), ForeignKey("schedule_activities.activity_id", ondelete="CASCADE"), nullable=False, index=True)
    rank = Column(Integer, nullable=False)
    overall_score = Column(Float, nullable=False)
    identifier_score = Column(Float, nullable=False)
    discipline_score = Column(Float, nullable=False)
    location_score = Column(Float, nullable=False)
    action_score = Column(Float, nullable=False)
    fuzzy_score = Column(Float, nullable=False)
    semantic_score = Column(Float, nullable=False)
    temporal_score = Column(Float, nullable=False)
    dependency_score = Column(Float, nullable=False)
    top_2_margin = Column(Float, nullable=True)
    matcher_version = Column(String(20), default="v1", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    event = relationship("ExtractedEvent", back_populates="candidates")
    activity = relationship("ScheduleActivity")
