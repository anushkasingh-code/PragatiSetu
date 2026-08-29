from sqlalchemy.orm import Session
from backend.app.db.models.project import Project
from backend.app.db.models.activity import ScheduleActivity

def get_project_timeline_data(project_id: str, db: Session) -> dict:
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise ValueError(f"Project with ID '{project_id}' not found.")

    activities = db.query(ScheduleActivity).filter(
        ScheduleActivity.project_id == project_id
    ).order_by(ScheduleActivity.wbs_id.asc(), ScheduleActivity.planned_start.asc()).all()

    activity_items = []
    for act in activities:
        activity_items.append({
            "activity_id": act.activity_id,
            "wbs_id": act.wbs_id,
            "discipline": act.discipline,
            "description": act.description,
            "location": act.location,
            "equipment_or_line_id": act.equipment_or_line_id,
            "planned_start": act.planned_start,
            "planned_finish": act.planned_finish,
            "actual_start": act.actual_start,
            "actual_finish": act.actual_finish,
            "percent_complete": act.percent_complete,
            "status": act.status,
            "predecessor_activity_id": act.predecessor_activity_id
        })

    return {
        "project_id": project.project_id,
        "project_name": project.name,
        "total_activities": len(activity_items),
        "activities": activity_items
    }
