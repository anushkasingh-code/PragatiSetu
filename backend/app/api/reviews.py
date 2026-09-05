from typing import Optional, List, Dict
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
    project_id: Optional[str] = None,
    limit: int = 1000,
    db: Session = Depends(get_db)
):
    """
    Returns pending human planner review items for a project in a single fast query.
    Aggregates ExtractedEvent, MatchDecision, MatchCandidate, and ScheduleActivity data.
    Ordered by SourceReport.created_at descending so newly uploaded DPRs and voice notes appear first.
    """
    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id parameter is required for review queries."
        )

    from backend.app.db.models.report import SourceReport
    from backend.app.db.models.event import ExtractedEvent
    from backend.app.db.models.decision import MatchDecision
    from backend.app.db.models.candidate import MatchCandidate
    from backend.app.db.models.activity import ScheduleActivity
    from backend.app.services.decision_service import DecisionService
    from backend.app.services.normalizer_service import normalize_project_id
    from backend.app.services.candidate_generator_service import CandidateGeneratorService
    from sqlalchemy import or_

    target_project = normalize_project_id(project_id)

    pending_decisions = {"HUMAN_REVIEW", "UNPLANNED_REVIEW", "CONFLICT_REVIEW"}

    reports = (
        db.query(SourceReport)
        .filter(or_(SourceReport.project_id == project_id, SourceReport.project_id == target_project))
        .order_by(SourceReport.created_at.desc())
        .all()
    )
    if not reports:
        return []

    report_map = {r.report_id: r for r in reports}
    report_ids = [r.report_id for r in reports]

    events = (
        db.query(ExtractedEvent)
        .filter(ExtractedEvent.report_id.in_(report_ids))
        .order_by(ExtractedEvent.created_at.desc())
        .all()
    )
    if not events:
        return []

    event_ids = [evt.event_id for evt in events]

    # Batch fetch existing decisions
    existing_decisions = (
        db.query(MatchDecision)
        .filter(MatchDecision.event_id.in_(event_ids))
        .all()
    )
    decision_map = {d.event_id: d for d in existing_decisions}

    # Evaluate any missing decisions
    dec_srv = None
    for evt in events:
        if evt.event_id not in decision_map:
            if dec_srv is None:
                dec_srv = DecisionService(db)
            try:
                _, dec = dec_srv.make_decision_for_event(evt.event_id)
                if dec:
                    decision_map[evt.event_id] = dec
            except Exception:
                continue

    # Filter for pending review events
    pending_events = [
        evt for evt in events
        if evt.event_id in decision_map and decision_map[evt.event_id].decision in pending_decisions
    ]
    if not pending_events:
        return []

    pending_event_ids = [evt.event_id for evt in pending_events]

    # Batch fetch candidates for pending events
    all_candidates = (
        db.query(MatchCandidate)
        .filter(MatchCandidate.event_id.in_(pending_event_ids))
        .order_by(MatchCandidate.rank.asc())
        .all()
    )
    cands_by_event: dict[str, list] = {}
    for c in all_candidates:
        cands_by_event.setdefault(c.event_id, []).append(c)

    # Auto-regenerate if candidates are missing or empty
    gen_srv = None
    for evt in pending_events:
        if not cands_by_event.get(evt.event_id):
            if gen_srv is None:
                gen_srv = CandidateGeneratorService(db)
            if dec_srv is None:
                dec_srv = DecisionService(db)
            try:
                _, cands, _ = gen_srv.generate_candidates_for_event(evt.event_id)
                _, dec = dec_srv.make_decision_for_event(evt.event_id)
                if dec:
                    decision_map[evt.event_id] = dec
                if cands:
                    cands_by_event[evt.event_id] = sorted(cands, key=lambda x: x.rank)
            except Exception:
                pass

    # Collect all activity IDs to fetch in a single query
    activity_ids_to_fetch = set()
    for evt in pending_events:
        for c in cands_by_event.get(evt.event_id, [])[:5]:
            if c.activity_id:
                activity_ids_to_fetch.add(c.activity_id)

    activity_map = {}
    if activity_ids_to_fetch:
        acts = (
            db.query(ScheduleActivity)
            .filter(ScheduleActivity.activity_id.in_(list(activity_ids_to_fetch)))
            .all()
        )
        for act in acts:
            activity_map[act.activity_id] = {
                "activity_id": act.activity_id,
                "description": act.description,
                "equipment_or_line_id": act.equipment_or_line_id or act.activity_id,
            }

    # Assemble response items
    items = []
    for evt in pending_events:
        dec = decision_map[evt.event_id]
        cands = cands_by_event.get(evt.event_id, [])[:5]

        cand_list = []
        item_acts = {}
        for c in cands:
            cand_list.append({
                "activity_id": c.activity_id,
                "rank": c.rank,
                "overall_score": round(c.overall_score, 1),
            })
            if c.activity_id in activity_map:
                item_acts[c.activity_id] = activity_map[c.activity_id]

        rep = report_map.get(evt.report_id)
        source_filename = rep.filename if rep else ""

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
                "source_filename": source_filename,
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

    return items


@router.post("/projects/{project_id}/reviews/reset-demo", status_code=status.HTTP_200_OK)
@router.post("/reviews/reset", status_code=status.HTTP_200_OK)
def reset_reviews_demo(
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Demo/testing convenience endpoint scoped to a specific project.
    Gated to non-production environments.
    Only resets match decisions and activities for the specified project.
    """
    from backend.app.config import settings
    if getattr(settings, "ENVIRONMENT", "production").lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Reset operations are disabled in production environment."
        )

    if not project_id or not project_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="project_id parameter is required for demo reviews reset."
        )

    from backend.app.db.models.report import SourceReport
    from backend.app.db.models.event import ExtractedEvent
    from backend.app.db.models.decision import MatchDecision
    from backend.app.db.models.activity import ScheduleActivity
    from backend.app.services.normalizer_service import normalize_project_id

    target_project = normalize_project_id(project_id)

    # Reset only decisions belonging to events in this project's reports
    report_ids = [
        r.report_id for r in db.query(SourceReport.report_id)
        .filter((SourceReport.project_id == project_id) | (SourceReport.project_id == target_project))
        .all()
    ]
    if report_ids:
        event_ids = [
            e.event_id for e in db.query(ExtractedEvent.event_id)
            .filter(ExtractedEvent.report_id.in_(report_ids))
            .all()
        ]
        if event_ids:
            db.query(MatchDecision).filter(MatchDecision.event_id.in_(event_ids)).update(
                {MatchDecision.decision: "HUMAN_REVIEW"}, synchronize_session=False
            )

    # Reset activities belonging strictly to this project
    db.query(ScheduleActivity).filter(
        (ScheduleActivity.project_id == project_id) | (ScheduleActivity.project_id == target_project)
    ).update({
        ScheduleActivity.status: "NOT_STARTED",
        ScheduleActivity.percent_complete: 0.0,
        ScheduleActivity.actual_start: None,
        ScheduleActivity.actual_finish: None,
    }, synchronize_session=False)

    db.commit()
    return {"status": "ok", "message": f"Demo reviews reset successfully for project '{project_id}'."}
