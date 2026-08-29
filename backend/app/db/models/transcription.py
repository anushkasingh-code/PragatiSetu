from datetime import datetime
import uuid
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

def generate_transcription_id():
    return f"TRX-{uuid.uuid4().hex[:8].upper()}"

class Transcription(Base):
    __tablename__ = "transcriptions"

    transcription_id = Column(String, primary_key=True, default=generate_transcription_id)
    project_id = Column(String, ForeignKey("projects.project_id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String, nullable=False)
    file_hash = Column(String, nullable=False, index=True)
    file_size = Column(Integer, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    language = Column(String, nullable=True, default="en")
    transcript = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="PENDING", index=True) # PENDING, PROCESSING, COMPLETED, FAILED
    model_name = Column(String, nullable=False, default="tiny")
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    project = relationship("Project", backref="transcriptions")
