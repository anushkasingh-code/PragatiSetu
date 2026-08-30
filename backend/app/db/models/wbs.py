from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column
from backend.app.db.database import Base

class WBSNode(Base):
    __tablename__ = "wbs_nodes"

    wbs_id: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    project_id: Mapped[str] = mapped_column(String(50), ForeignKey("projects.project_id", ondelete="CASCADE"), nullable=False, index=True)
    parent_wbs_id: Mapped[str | None] = mapped_column(String(50), ForeignKey("wbs_nodes.wbs_id", ondelete="SET NULL"), nullable=True, index=True)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    project = relationship("Project", back_populates="wbs_nodes")
    parent = relationship("WBSNode", remote_side=[wbs_id], back_populates="children")
    children = relationship("WBSNode", back_populates="parent", cascade="all, delete-orphan")
    activities = relationship("ScheduleActivity", back_populates="wbs_node")
