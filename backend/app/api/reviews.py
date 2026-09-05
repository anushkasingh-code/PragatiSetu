from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.schemas.review import HumanReviewRequest, HumanReviewResponse
from backend.app.services.human_review_service import process_human_review_decision

router = APIRouter(tags=["Human Planner Review"])

@router.post("/reviews/{event_id}/decision", response_model=HumanReviewResponse, status_code=status.HTTP_200_OK)
def submit_human_review_decision(event_id: str, payload: HumanReviewRequest, db: Session = Depends(get_db)):
    """
    Submits a human planner review decision for an event requiring review or override.
    Supports decision choices: ACCEPT, SWITCH, REJECT, UNPLANNED.
    Invokes state validation, atomic schedule progress updates, and audit logging when accepted/switched.
    """
    try:
        res = process_human_review_decision(
            event_id=event_id,
            decision_type=payload.decision,
            selected_activity_id=payload.selected_activity_id,
            reason=payload.reason,
            db=db
        )
        return res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing human review decision: {str(e)}"
        )


@router.get("/projects/{project_id}/reviews/pending", status_code=status.HTTP_200_OK)
@router.get("/reviews/pending", status_code=status.HTTP_200_OK)
def get_pending_reviews(
    project_id: str = "PROJ-ALPHA",
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    Returns pending human planner review items for a project in a single fast query.
    Aggregates ExtractedEvent, MatchDecision, MatchCandidate, and ScheduleActivity data.
    Ordered by SourceReport.created_at descending so newly uploaded DPRs and voice notes appear first.
    """
    from backend.app.db.models.report import SourceReport
    from backend.app.db.models.event import ExtractedEvent
    from backend.app.db.models.decision import MatchDecision
    from backend.app.db.models.candidate import MatchCandidate
    from backend.app.db.models.activity import ScheduleActivity
    from backend.app.services.decision_service import DecisionService

    target_project = project_id or "PROJ-ALPHA"
    if target_project in ("PRAGATI-01", "24P201"):
        target_project = "PROJ-ALPHA"

    pending_decisions = {"HUMAN_REVIEW", "UNPLANNED_REVIEW", "CONFLICT_REVIEW"}

    reports = (
        db.query(SourceReport)
        .filter(SourceReport.project_id == target_project)
        .order_by(SourceReport.created_at.desc())
        .all()
    )

    items = []
    act_cache: dict[str, dict] = {}

    for rep in reports:
        events = (
            db.query(ExtractedEvent)
            .filter(ExtractedEvent.report_id == rep.report_id)
            .order_by(ExtractedEvent.created_at.desc())
            .all()
        )
        for evt in events:
            dec = db.query(MatchDecision).filter(MatchDecision.event_id == evt.event_id).first()
            if not dec:
                try:
                    dec_srv = DecisionService(db)
                    _, dec = dec_srv.make_decision_for_event(evt.event_id)
                except Exception:
                    continue

            if not dec or dec.decision not in pending_decisions:
                continue

            cands = (
                db.query(MatchCandidate)
                .filter(MatchCandidate.event_id == evt.event_id)
                .order_by(MatchCandidate.rank.asc())
                .limit(5)
                .all()
            )

            cand_list = []
            item_acts = {}
            for c in cands:
                cand_list.append({
                    "activity_id": c.activity_id,
                    "rank": c.rank,
                    "overall_score": round(c.overall_score, 1),
                })
                if c.activity_id not in act_cache:
                    act = db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == c.activity_id).first()
                    if act:
                        act_cache[c.activity_id] = {
                            "activity_id": act.activity_id,
                            "description": act.description,
                            "equipment_or_line_id": act.equipment_or_line_id or act.activity_id,
                        }
                if c.activity_id in act_cache:
                    item_acts[c.activity_id] = act_cache[c.activity_id]

            items.append({
                "event": {
                    "event_id": evt.event_id,
                    "report_id": evt.report_id,
                    "raw_text": evt.raw_text,
                    "identifier": evt.identifier,
                    "action": evt.action,
                    "object": evt.object,
                    "location": evt.location,
                    "status": evt.status,
                    "percent_complete": evt.percent_complete,
                    "event_date": str(evt.event_date) if evt.event_date else None,
                    "source_filename": rep.filename,
                },
                "decision": {
                    "event_id": dec.event_id,
                    "decision": dec.decision,
                    "top_activity_id": dec.top_activity_id,
                    "match_confidence": round(dec.match_confidence, 1),
                    "reasons": dec.reasons or [],
                },
                "candidates": cand_list,
                "activities": item_acts,
                "isFallback": False
            })

            if len(items) >= limit:
                break
        if len(items) >= limit:
            break

    return items


@router.post("/reviews/reset", status_code=status.HTTP_200_OK)
def reset_reviews_demo(db: Session = Depends(get_db)):
    """
    Convenience endpoint for demo/testing.
    Resets all match decisions back to HUMAN_REVIEW and resets schedule activities to NOT_STARTED.
    """
    from backend.app.db.models.decision import MatchDecision
    from backend.app.db.models.activity import ScheduleActivity
    from backend.app.db.models.audit import AuditRecord

    db.query(MatchDecision).update({MatchDecision.decision: "HUMAN_REVIEW"})
    db.query(ScheduleActivity).filter(ScheduleActivity.activity_id.in_(["CIV-101", "CIV-114"])).update({
        ScheduleActivity.status: "NOT_STARTED",
        ScheduleActivity.percent_complete: 0.0,
        ScheduleActivity.actual_start: None,
        ScheduleActivity.actual_finish: None,
    }, synchronize_session=False)
    db.commit()
    return {"status": "ok", "message": "Demo reviews reset successfully."}
