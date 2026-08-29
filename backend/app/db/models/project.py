from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class Project(Base):
    __tablename__ = "projects"

    project_id = Column(String(50), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    wbs_nodes = relationship("WBSNode", back_populates="project", cascade="all, delete-orphan")
    activities = relationship("ScheduleActivity", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("SourceReport", back_populates="project", cascade="all, delete-orphan")
