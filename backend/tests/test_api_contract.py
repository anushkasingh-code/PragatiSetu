import os
import pytest
from datetime import date
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.db.models.project import Project
from backend.app.db.models.activity import ScheduleActivity
from backend.app.db.models.report import SourceReport
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.decision import MatchDecision

@pytest.fixture(autouse=True)
def setup_data(db_session):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    if os.path.exists(dataset_path):
        importer = BaselineImporter(db_session)
        importer.import_excel_baseline(dataset_path)

def create_event(db_session, event_id="EVT-CONTRACT-01"):
    rep = db_session.query(SourceReport).filter(SourceReport.project_id == "PROJ-ALPHA").first()
    if not rep:
        rep = SourceReport(
            report_id="REP-PROJ-ALPHA",
            project_id="PROJ-ALPHA",
            filename="report.txt",
            source_type="TXT",
            report_date=date(2026, 1, 5),
            file_hash="contracthash123",
            file_size=100,
            stored_path="pathcontract",
            processing_status="VALIDATED"
        )
        db_session.add(rep)
        db_session.commit()

    evt = ExtractedEvent(
        event_id=event_id,
        report_id=rep.report_id,
        raw_text="24P201 spool erection started near Rack B",
        event_date=date(2026, 1, 5),
        discipline="Piping",
        action="erection",
        object="spool",
        identifier="24P201",
        location="Rack B",
        status="STARTED",
        extraction_method="RULE_BASED",
        extraction_version="v1"
    )
    db_session.add(evt)
    db_session.commit()

    act = db_session.query(ScheduleActivity).filter(ScheduleActivity.project_id == "PROJ-ALPHA").first()
    act_id = act.activity_id if act else "PIP-201"

    dec = MatchDecision(
        decision_id=f"DEC-{event_id}",
        event_id=event_id,
        top_activity_id=act_id,
        match_confidence=92.0,
        evidence_completeness=100.0,
        top_2_margin=20.0,
        decision="HUMAN_REVIEW",
        reasons=["Ambiguous test match requiring human review"],
        missing_evidence=[],
        matcher_version="v1",
        scoring_policy_version="v1"
    )
    db_session.add(dec)
    db_session.commit()
    return evt

def test_1_create_project_api(client):
    res = client.post("/projects", json={
        "project_id": "PROJ-NEW-01",
        "name": "New Terminal Project",
        "description": "Test project description"
    })
    assert res.status_code == 201
    body = res.json()
    assert body["project_id"] == "PROJ-NEW-01"
    assert body["name"] == "New Terminal Project"

def test_2_project_details_api(client):
    res = client.get("/projects/PROJ-ALPHA")
    assert res.status_code == 200
    assert res.json()["project_id"] == "PROJ-ALPHA"

def test_3_timeline_api(client):
    res = client.get("/projects/PROJ-ALPHA/timeline")
    assert res.status_code == 200
    body = res.json()
    assert body["project_id"] == "PROJ-ALPHA"
    assert len(body["activities"]) > 0
    first_act = body["activities"][0]
    assert "planned_start" in first_act
    assert "planned_finish" in first_act

def test_4_dashboard_api(client):
    res = client.get("/projects/PROJ-ALPHA/dashboard")
    assert res.status_code == 200
    body = res.json()
    assert body["project_id"] == "PROJ-ALPHA"
    assert body["total_activities"] > 0

def test_5_global_audit_query_api(client):
    res = client.get("/audit?project_id=PROJ-ALPHA&limit=10")
    assert res.status_code == 200
    assert isinstance(res.json(), list)

def test_6_human_review_accept(client, db_session):
    evt = create_event(db_session, event_id="EVT-REV-ACCEPT")
    act = db_session.query(ScheduleActivity).filter(ScheduleActivity.project_id == "PROJ-ALPHA").first()
    act_id = act.activity_id if act else "PIP-201"
    res = client.post("/reviews/EVT-REV-ACCEPT/decision", json={
        "decision": "ACCEPT",
        "selected_activity_id": act_id,
        "reason": "Confirmed by Lead Planner"
    })
    assert res.status_code == 200
    body = res.json()
    assert body["decision"] == "ACCEPT"
    assert body["applied"] is True

def test_7_human_review_switch(client, db_session):
    evt = create_event(db_session, event_id="EVT-REV-SWITCH")
    acts = db_session.query(ScheduleActivity).filter(ScheduleActivity.project_id == "PROJ-ALPHA").all()
    switch_act_id = acts[1].activity_id if len(acts) > 1 else "PIP-202"
    res = client.post("/reviews/EVT-REV-SWITCH/decision", json={
        "decision": "SWITCH",
        "selected_activity_id": switch_act_id,
        "reason": "Switched to adjacent spool activity"
    })
    assert res.status_code == 200
    body = res.json()
    assert body["decision"] == "SWITCH"
    assert body["selected_activity_id"] == switch_act_id

def test_8_human_review_reject(client, db_session):
    create_event(db_session, event_id="EVT-REV-REJECT")
    res = client.post("/reviews/EVT-REV-REJECT/decision", json={
        "decision": "REJECT",
        "reason": "Incorrect field report entry"
    })
    assert res.status_code == 200
    body = res.json()
    assert body["decision"] == "REJECT"
    assert body["applied"] is False

def test_9_standardized_error_format(client):
    res = client.get("/projects/NONEXISTENT-PROJ-ID")
    assert res.status_code == 404
    body = res.json()
    assert "error" in body
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "message" in body["error"]

def test_10_openapi_docs(client):
    res = client.get("/openapi.json")
    assert res.status_code == 200
    spec = res.json()
    assert "paths" in spec
    assert "/projects" in spec["paths"]
    assert "/reports/upload" in spec["paths"]

def test_11_placeholders_api(client):
    r1 = client.get("/metrics")
    assert r1.status_code == 200
    assert r1.json()["system_status"] == "healthy"
