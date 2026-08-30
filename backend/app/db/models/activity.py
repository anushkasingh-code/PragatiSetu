from sqlalchemy import Column, String, Text, Date, Float, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.db.database import Base
from datetime import date

class ScheduleActivity(Base):
    __tablename__ = "schedule_activities"

    activity_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    wbs_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("wbs_nodes.wbs_id", ondelete="SET NULL"), nullable=True, index=True)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    equipment_or_line_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)

    # Baseline planned schedule (IMMUTABLE)
    planned_start: Mapped[date] = mapped_column(Date, nullable=False)
    planned_finish: Mapped[date] = mapped_column(Date, nullable=False)

    # Actual schedule progress (SEPARATE & MUTABLE)
    actual_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_finish: Mapped[date | None] = mapped_column(Date, nullable=True)
    percent_complete: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="NOT_STARTED", nullable=False)

    predecessor_activity_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("schedule_activities.activity_id", ondelete="SET NULL"), nullable=True)

    project = relationship("Project", back_populates="activities")
    wbs_node = relationship("WBSNode", back_populates="activities")
