from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.db.database import get_db
from backend.app.db.models.audit import AuditRecord
from backend.app.schemas.audit import AuditRecordResponse

router = APIRouter(tags=["Audit Trail"])

@router.get("/audit", response_model=List[AuditRecordResponse])
def query_audit_trail(
    project_id: Optional[str] = Query(None, description="Filter audit logs by project ID"),
    activity_id: Optional[str] = Query(None, description="Filter audit logs by activity ID"),
    event_id: Optional[str] = Query(None, description="Filter audit logs by event ID"),
    report_id: Optional[str] = Query(None, description="Filter audit logs by report ID"),
    limit: int = Query(50, ge=1, le=500, description="Max audit entries to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db)
):
    """
    Retrieves immutable historical audit records for inspection.
    Supports optional query filters: project_id, activity_id, event_id, report_id, limit, offset.
    Exposes BEFORE (previous_value) and AFTER (new_value) JSON snapshots, decision, and confidence.
    """
    query = db.query(AuditRecord)
    if project_id:
        query = query.filter(AuditRecord.project_id == project_id)
    if activity_id:
        query = query.filter(AuditRecord.activity_id == activity_id)
    if event_id:
        query = query.filter(AuditRecord.event_id == event_id)
    if report_id:
        query = query.filter(AuditRecord.report_id == report_id)

    records = query.order_by(AuditRecord.timestamp.desc()).offset(offset).limit(limit).all()
    return records

@router.post("/audit/clear", status_code=status.HTTP_200_OK)
def clear_audit_trail(
    project_id: Optional[str] = Query(None, description="Project ID to clear demo audit logs for"),
    db: Session = Depends(get_db)
):
    """
    Clears audit records strictly scoped to a specific project.
    Gated to non-production environments; production audit trail is append-only and immutable.
    """
    if getattr(settings, "ENVIRONMENT", "production").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit trail is immutable in production. Clear operation is disabled."
        )

    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id parameter is required to clear audit records."
        )

    from backend.app.services.normalizer_service import normalize_project_id
    target_project = normalize_project_id(project_id)

    deleted_count = db.query(AuditRecord).filter(
        (AuditRecord.project_id == project_id) | (AuditRecord.project_id == target_project)
    ).delete(synchronize_session=False)
    db.commit()
    return {
        "status": "cleared",
        "message": f"Audit trail cleared successfully for project '{project_id}'.",
        "deleted_count": deleted_count
    }
