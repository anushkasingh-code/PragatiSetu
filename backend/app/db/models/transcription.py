from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.db.database import Base

def generate_transcription_id():
    return f"TRX-{uuid.uuid4().hex[:8].upper()}"

class Transcription(Base):
    __tablename__ = "transcriptions"

    transcription_id: Mapped[str] = mapped_column(String, primary_key=True, default=generate_transcription_id)
    project_id: Mapped[str | None] = mapped_column(String, ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True, index=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[str] = mapped_column(String, nullable=False, index=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    language: Mapped[str | None] = mapped_column(String, nullable=True, default="en")
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING", index=True) # PENDING, PROCESSING, COMPLETED, FAILED
    model_name: Mapped[str] = mapped_column(String, nullable=False, default="tiny")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    project = relationship("Project", backref="transcriptions")
