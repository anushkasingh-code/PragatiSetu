from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.db.database import Base

class Project(Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    wbs_nodes = relationship("WBSNode", back_populates="project", cascade="all, delete-orphan")
    activities = relationship("ScheduleActivity", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("SourceReport", back_populates="project", cascade="all, delete-orphan")
