from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.app.db.models.project import Project
from backend.app.db.models.activity import ScheduleActivity
from backend.app.db.models.report import SourceReport
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.decision import MatchDecision
from backend.app.db.models.audit import AuditRecord

def get_project_dashboard_summary(project_id: str, db: Session) -> dict:
    project = db.query(Project).filter(Project.project_id == project_id).first()
    if not project:
        raise ValueError(f"Project with ID '{project_id}' not found.")

    activities = db.query(ScheduleActivity).filter(ScheduleActivity.project_id == project_id)
    total_activities = activities.count()
    completed_activities = activities.filter(ScheduleActivity.status == "COMPLETED").count()
    in_progress_activities = activities.filter(ScheduleActivity.status == "IN_PROGRESS").count()
    started_activities = activities.filter(ScheduleActivity.status == "STARTED").count()
    not_started_activities = activities.filter(ScheduleActivity.status == "NOT_STARTED").count()

    # Calculate real weighted average progress across all activities
    if total_activities > 0:
        avg_pct = db.query(func.avg(ScheduleActivity.percent_complete)).filter(ScheduleActivity.project_id == project_id).scalar() or 0.0
        progress_percentage = round(float(avg_pct), 1)
    else:
        progress_percentage = 0.0

    reports = db.query(SourceReport).filter(SourceReport.project_id == project_id)
    total_reports = reports.count()
    duplicate_reports = reports.filter(SourceReport.processing_status == "DUPLICATE").count()

    events_query = db.query(ExtractedEvent).join(SourceReport, ExtractedEvent.report_id == SourceReport.report_id).filter(SourceReport.project_id == project_id)
    total_events = events_query.count()

    decisions_query = db.query(MatchDecision).join(ExtractedEvent, MatchDecision.event_id == ExtractedEvent.event_id).join(SourceReport, ExtractedEvent.report_id == SourceReport.report_id).filter(SourceReport.project_id == project_id)
    auto_linked_events = decisions_query.filter(MatchDecision.decision == "AUTO_LINK").count()
    human_review_events = decisions_query.filter(MatchDecision.decision == "HUMAN_REVIEW").count()
    unplanned_events = decisions_query.filter(MatchDecision.decision == "UNPLANNED_REVIEW").count()

    conflict_events = decisions_query.filter(MatchDecision.decision == "CONFLICT_REVIEW").count()
    ignore_events = decisions_query.filter(MatchDecision.decision == "IGNORE").count()
    applied_events = db.query(AuditRecord).filter(AuditRecord.project_id == project_id).count()

    return {
        "project_id": project.project_id,
        "project_name": project.name,
        "total_activities": total_activities,
        "completed_activities": completed_activities,
        "in_progress_activities": in_progress_activities,
        "started_activities": started_activities,
        "not_started_activities": not_started_activities,
        "progress_percentage": progress_percentage,
        "total_reports": total_reports,
        "total_events": total_events,
        "auto_linked_events": auto_linked_events,
        "human_review_events": human_review_events,
        "unplanned_events": unplanned_events,
        "conflict_events": conflict_events,
        "ignore_events": ignore_events,
        "applied_events": applied_events,
        "duplicate_reports": duplicate_reports
    }
