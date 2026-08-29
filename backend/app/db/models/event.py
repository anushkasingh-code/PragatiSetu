from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, Date, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class ExtractedEvent(Base):
    __tablename__ = "extracted_events"

    event_id = Column(String(50), primary_key=True, index=True)
    report_id = Column(String(50), ForeignKey("source_reports.report_id", ondelete="CASCADE"), nullable=False, index=True)
    raw_text = Column(Text, nullable=False)
    event_date = Column(Date, nullable=True)
    event_date_source = Column(String(20), nullable=True)
    discipline = Column(String(100), nullable=True)
    action = Column(String(150), nullable=True)
    object = Column(String(150), nullable=True)
    identifier = Column(String(100), nullable=True, index=True)
    location = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True, index=True)
    percent_complete = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    source_position = Column(JSON, nullable=True)
    extraction_method = Column(String(50), default="RULE_BASED", nullable=False)
    extraction_version = Column(String(20), default="v1", nullable=False)
    
    # Milestone 4: Normalized Representation
    normalized_identifier = Column(String(100), nullable=True, index=True)
    normalized_action = Column(String(150), nullable=True)
    normalized_object = Column(String(150), nullable=True)
    normalized_location = Column(String(255), nullable=True)
    normalization_version = Column(String(20), default="v1", nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    report = relationship("SourceReport", back_populates="events")
    candidates = relationship("MatchCandidate", back_populates="event", cascade="all, delete-orphan")
