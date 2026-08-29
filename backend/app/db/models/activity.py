from sqlalchemy import Column, String, Text, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class ScheduleActivity(Base):
    __tablename__ = "schedule_activities"

    activity_id = Column(String(50), primary_key=True, index=True)
    project_id = Column(String(50), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    wbs_id = Column(String(50), ForeignKey("wbs_nodes.wbs_id", ondelete="SET NULL"), nullable=True, index=True)
    discipline = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=False)
    location = Column(String(255), nullable=True)
    equipment_or_line_id = Column(String(100), nullable=True, index=True)

    # Baseline planned schedule (IMMUTABLE)
    planned_start = Column(Date, nullable=False)
    planned_finish = Column(Date, nullable=False)

    # Actual schedule progress (SEPARATE & MUTABLE)
    actual_start = Column(Date, nullable=True)
    actual_finish = Column(Date, nullable=True)
    percent_complete = Column(Float, default=0.0, nullable=False)
    status = Column(String(50), default="NOT_STARTED", nullable=False)

    predecessor_activity_id = Column(String(50), ForeignKey("schedule_activities.activity_id", ondelete="SET NULL"), nullable=True)

    project = relationship("Project", back_populates="activities")
    wbs_node = relationship("WBSNode", back_populates="activities")
