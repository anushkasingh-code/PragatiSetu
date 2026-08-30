from datetime import datetime, timezone, date
from sqlalchemy import Column, String, Text, Date, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.db.database import Base
from typing import Any

class ExtractedEvent(Base):
    __tablename__ = "extracted_events"

    event_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    report_id: Mapped[str] = mapped_column(String(50), ForeignKey("source_reports.report_id", ondelete="CASCADE"), nullable=False, index=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    event_date_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    discipline: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action: Mapped[str | None] = mapped_column(String(150), nullable=True)
    object: Mapped[str | None] = mapped_column(String(150), nullable=True)
    identifier: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    percent_complete: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_position: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    extraction_method: Mapped[str] = mapped_column(String(50), default="RULE_BASED", nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(20), default="v1", nullable=False)
    
    # Milestone 4: Normalized Representation
    normalized_identifier: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    normalized_action: Mapped[str | None] = mapped_column(String(150), nullable=True)
    normalized_object: Mapped[str | None] = mapped_column(String(150), nullable=True)
    normalized_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    normalization_version: Mapped[str | None] = mapped_column(String(20), default="v1", nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    report = relationship("SourceReport", back_populates="events")
    candidates = relationship("MatchCandidate", back_populates="event", cascade="all, delete-orphan")
