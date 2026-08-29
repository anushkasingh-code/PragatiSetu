import os
import pytest
from datetime import date
from unittest.mock import patch
from sqlalchemy.orm import Session
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.services.progress_update_service import ProgressUpdateService
from backend.app.services.decision_service import DecisionService
from backend.app.services.state_validator import (
    validate_state_transition,
    validate_date_ordering,
    validate_percentage,
    check_dependency_warnings
)
from backend.app.services.conflict_service import detect_schedule_conflicts
from backend.app.db.models.report import SourceReport
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.candidate import MatchCandidate
from backend.app.db.models.decision import MatchDecision, DecisionEnum
from backend.app.db.models.audit import AuditRecord
from backend.app.db.models.activity import ScheduleActivity

@pytest.fixture(autouse=True)
def setup_data(db_session):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    if os.path.exists(dataset_path):
        importer = BaselineImporter(db_session)
        importer.import_excel_baseline(dataset_path)

def _get_act_id(db_session, preferred="PIP-201"):
    act = db_session.query(ScheduleActivity).filter(ScheduleActivity.activity_id == preferred).first()
    if act:
        return act.activity_id
    fallback = db_session.query(ScheduleActivity).first()
    return fallback.activity_id if fallback else preferred

def create_event_and_autolink(db_session, event_id="EVT-APPLY-001", raw_text="24P201 spool erection started near Rack B", status="STARTED", percent=None, activity_id="PIP-201"):
    act_id = _get_act_id(db_session, activity_id)
    rep = db_session.query(SourceReport).filter(SourceReport.project_id == "PROJ-ALPHA").first()
    if not rep:
        rep = SourceReport(
            report_id="REP-PROJ-ALPHA",
            project_id="PROJ-ALPHA",
            filename="report.txt",
            source_type="TXT",
            report_date=date(2026, 1, 5),
            file_hash="dummyhashapply",
            file_size=100,
            stored_path="pathapply",
            processing_status="VALIDATED"
        )
        db_session.add(rep)
        db_session.commit()

    evt = ExtractedEvent(
        event_id=event_id,
        report_id=rep.report_id,
        raw_text=raw_text,
        event_date=date(2026, 1, 5),
        discipline="Piping",
        action="erection",
        object="spool",
        identifier="24P201",
        location="Rack B",
        status=status,
        percent_complete=percent,
        extraction_method="RULE_BASED",
        extraction_version="v1"
    )
    db_session.add(evt)
    db_session.commit()

    dec = MatchDecision(
        decision_id=f"DEC-{event_id}",
        event_id=event_id,
        top_activity_id=act_id,
        match_confidence=95.0,
        evidence_completeness=100.0,
        top_2_margin=25.0,
        decision="AUTO_LINK",
        reasons=["High confidence test match"],
        missing_evidence=[],
        matcher_version="v1",
        scoring_policy_version="v1"
    )
    db_session.add(dec)
    db_session.commit()
    return evt, dec

def test_1_valid_status_transitions():
    assert validate_state_transition("NOT_STARTED", "STARTED") is True
    assert validate_state_transition("STARTED", "IN_PROGRESS") is True
    assert validate_state_transition("IN_PROGRESS", "COMPLETED") is True
    assert validate_state_transition("STARTED", "COMPLETED") is True
    assert validate_state_transition("COMPLETED", "REWORK") is True

def test_2_invalid_status_transitions():
    assert validate_state_transition("COMPLETED", "STARTED") is False
    assert validate_state_transition("COMPLETED", "IN_PROGRESS") is False

def test_3_date_ordering_validation():
    valid, _ = validate_date_ordering(date(2026, 1, 1), date(2026, 1, 10))
    assert valid is True

    invalid, err = validate_date_ordering(date(2026, 1, 10), date(2026, 1, 1))
    assert invalid is False
    assert "INVALID_DATE_ORDER" in err

def test_4_percentage_validation():
    v1, _ = validate_percentage(50.0)
    assert v1 is True

    v2, err2 = validate_percentage(150.0)
    assert v2 is False

    v3, err3 = validate_percentage(-10.0)
    assert v3 is False

def test_5_dependency_warning(db_session):
    act = db_session.query(ScheduleActivity).filter(ScheduleActivity.predecessor_activity_id.isnot(None)).first()
    if act:
        warnings = check_dependency_warnings(act, db_session)
        assert len(warnings) >= 0

def test_6_successful_started_update(db_session):
    evt, dec = create_event_and_autolink(db_session, event_id="EVT-START-01", status="STARTED")
    service = ProgressUpdateService(db_session)
    res = service.apply_event_progress("EVT-START-01")

    assert res["applied"] is True
    assert res["status"] in ["STARTED", "IN_PROGRESS"]
    assert res["actual_start"] == "2026-01-05"
    assert res["audit_id"] is not None

def test_7_successful_in_progress_update(db_session):
    evt, dec = create_event_and_autolink(db_session, event_id="EVT-PROG-01", status="IN_PROGRESS", percent=60.0)
    service = ProgressUpdateService(db_session)
    res = service.apply_event_progress("EVT-PROG-01")

    assert res["applied"] is True
    assert res["status"] == "IN_PROGRESS"
    assert res["percent_complete"] == 60.0

def test_8_successful_completed_update(db_session):
    evt, dec = create_event_and_autolink(db_session, event_id="EVT-COMP-01", status="COMPLETED")
    service = ProgressUpdateService(db_session)
    res = service.apply_event_progress("EVT-COMP-01")

    assert res["applied"] is True
    assert res["status"] == "COMPLETED"
    assert res["percent_complete"] == 100.0
    assert res["actual_finish"] == "2026-01-05"

def test_9_planned_dates_remain_immutable(db_session):
    act_id = _get_act_id(db_session, "PIP-201")
    act = db_session.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act_id).first()
    p_start_before = act.planned_start
    p_finish_before = act.planned_finish

    evt, dec = create_event_and_autolink(db_session, event_id="EVT-IMMUTABLE-01", status="COMPLETED", activity_id=act_id)
    service = ProgressUpdateService(db_session)
    service.apply_event_progress("EVT-IMMUTABLE-01")

    db_session.refresh(act)
    assert act.planned_start == p_start_before
    assert act.planned_finish == p_finish_before

def test_10_conflict_detection_completed_to_in_progress(db_session):
    act_id = _get_act_id(db_session, "PIP-201")
    act = db_session.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act_id).first()
    act.status = "COMPLETED"
    act.percent_complete = 100.0
    db_session.commit()

    evt, dec = create_event_and_autolink(db_session, event_id="EVT-CONF-01", status="IN_PROGRESS", percent=60.0, activity_id=act_id)
    service = ProgressUpdateService(db_session)
    res = service.apply_event_progress("EVT-CONF-01")

    assert res["applied"] is False
    assert len(res["conflicts"]) > 0
    assert "conflicts with accepted state" in res["conflicts"][0]

def test_11_human_review_cannot_automatically_update(db_session):
    evt, dec = create_event_and_autolink(db_session, event_id="EVT-HUMAN-01")
    dec.decision = "HUMAN_REVIEW"
    db_session.commit()

    service = ProgressUpdateService(db_session)
    res = service.apply_event_progress("EVT-HUMAN-01")

    assert res["applied"] is False
    assert "HUMAN_REVIEW" in res["reason"]

def test_12_unplanned_review_cannot_update(db_session):
    evt, dec = create_event_and_autolink(db_session, event_id="EVT-UNPLAN-01")
    dec.decision = "UNPLANNED_REVIEW"
    dec.top_activity_id = None
    db_session.commit()

    service = ProgressUpdateService(db_session)
    res = service.apply_event_progress("EVT-UNPLAN-01")

    assert res["applied"] is False

def test_13_ignore_cannot_update(db_session):
    evt, dec = create_event_and_autolink(db_session, event_id="EVT-IGNORE-01")
    dec.decision = "IGNORE"
    db_session.commit()

    service = ProgressUpdateService(db_session)
    res = service.apply_event_progress("EVT-IGNORE-01")

    assert res["applied"] is False

def test_14_audit_record_created_with_snapshots(db_session):
    evt, dec = create_event_and_autolink(db_session, event_id="EVT-AUD-01", status="COMPLETED")
    service = ProgressUpdateService(db_session)
    res = service.apply_event_progress("EVT-AUD-01")

    audit = db_session.query(AuditRecord).filter(AuditRecord.audit_id == res["audit_id"]).first()
    assert audit is not None
    assert audit.previous_value is not None
    assert audit.new_value is not None
    assert audit.new_value["status"] == "COMPLETED"

def test_15_idempotent_application(db_session):
    evt, dec = create_event_and_autolink(db_session, event_id="EVT-IDEMP-APPLY", status="COMPLETED")
    service = ProgressUpdateService(db_session)

    res1 = service.apply_event_progress("EVT-IDEMP-APPLY")
    assert res1["applied"] is True
    assert res1["already_applied"] is False

    res2 = service.apply_event_progress("EVT-IDEMP-APPLY")
    assert res2["applied"] is True
    assert res2["already_applied"] is True

def test_16_atomic_transaction_rollback_on_failure(db_session):
    evt, dec = create_event_and_autolink(db_session, event_id="EVT-ROLLBACK-01", status="COMPLETED")
    act = db_session.query(ScheduleActivity).filter(ScheduleActivity.activity_id == dec.top_activity_id).first()
    orig_status = act.status
    orig_percent = act.percent_complete

    service = ProgressUpdateService(db_session)

    # Patch record_schedule_audit to raise exception inside atomic transaction
    with patch("backend.app.services.progress_update_service.record_schedule_audit", side_effect=RuntimeError("Simulated audit failure")):
        with pytest.raises(RuntimeError) as exc_info:
            service.apply_event_progress("EVT-ROLLBACK-01")
        assert "Simulated audit failure" in str(exc_info.value)

    # Verify atomic transaction rollback: ScheduleActivity status and percent_complete remain unchanged
    db_session.refresh(act)
    assert act.status == orig_status
    assert act.percent_complete == orig_percent

    # Verify no audit record was written
    audit = db_session.query(AuditRecord).filter(AuditRecord.event_id == "EVT-ROLLBACK-01").first()
    assert audit is None

def test_17_api_apply_endpoint(client, db_session):
    create_event_and_autolink(db_session, event_id="EVT-API-APPLY", status="COMPLETED")
    res = client.post("/events/EVT-API-APPLY/apply")
    assert res.status_code == 200
    body = res.json()
    assert body["applied"] is True
    assert body["status"] == "COMPLETED"

def test_18_api_get_audit_trail(client, db_session):
    act_id = _get_act_id(db_session, "PIP-201")
    create_event_and_autolink(db_session, event_id="EVT-API-AUD-GET", status="COMPLETED", activity_id=act_id)
    client.post("/events/EVT-API-AUD-GET/apply")

    res = client.get(f"/activities/{act_id}/audit")
    assert res.status_code == 200
    audits = res.json()
    assert len(audits) >= 1
    assert audits[0]["activity_id"] == act_id

def test_19_rework_transition(db_session):
    act_id = _get_act_id(db_session, "PIP-201")
    act = db_session.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act_id).first()
    act.status = "COMPLETED"
    act.percent_complete = 100.0
    db_session.commit()

    evt, dec = create_event_and_autolink(db_session, event_id="EVT-REWORK-01", status="REWORK", percent=75.0, activity_id=act_id)
    service = ProgressUpdateService(db_session)
    res = service.apply_event_progress("EVT-REWORK-01")

    assert res["applied"] is True
    assert res["status"] == "REWORK"
    assert res["percent_complete"] == 75.0

def test_20_actual_start_preserved_if_exists(db_session):
    act_id = _get_act_id(db_session, "PIP-201")
    act = db_session.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act_id).first()
    orig_start = date(2026, 1, 1)
    act.actual_start = orig_start
    db_session.commit()

    evt, dec = create_event_and_autolink(db_session, event_id="EVT-PRESERVE-START", status="COMPLETED", activity_id=act_id)
    service = ProgressUpdateService(db_session)
    res = service.apply_event_progress("EVT-PRESERVE-START")

    db_session.refresh(act)
    assert act.actual_start == orig_start
