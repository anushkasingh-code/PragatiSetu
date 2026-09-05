import os
import io
import pytest
from datetime import date
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.db.database import Base, get_db
from backend.app.db.models.project import Project
from backend.app.db.models.activity import ScheduleActivity
from backend.app.db.models.report import SourceReport, ProcessingStatus
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.decision import MatchDecision, DecisionEnum
from backend.app.db.models.audit import AuditRecord
from backend.app.services.normalizer_service import normalize_project_id
from backend.app.services.decision_service import DecisionService
from backend.app.services.progress_update_service import ProgressUpdateService
from backend.app.services.conflict_service import detect_schedule_conflicts

def test_full_e2e_smoke(client, db_session):
    """
    Complete 20-step End-to-End smoke test validating all PragatiSetu core flows.
    """
    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    # 2. Verify OpenApi docs
    res = client.get("/docs")
    assert res.status_code == 200

    # 3. Create project
    proj_payload = {
        "project_id": "PROJ-ALPHA",
        "name": "Smoke Test Terminal",
        "description": "Validation project for E2E flow"
    }
    res = client.post("/projects", json=proj_payload)
    assert res.status_code == 201
    created_proj = res.json()
    assert created_proj["project_id"] == "PROJ-ALPHA"
    assert created_proj["total_activities"] == 0
    assert created_proj["progress_percentage"] == 0.0

    # 4. Fetch project by ID
    res = client.get("/projects/PROJ-ALPHA")
    assert res.status_code == 200
    assert res.json()["name"] == "Smoke Test Terminal"

    # 5. Import baseline schedule
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    assert os.path.exists(dataset_path), "Baseline dataset file must exist"

    with open(dataset_path, "rb") as f:
        file_bytes = f.read()

    res = client.post(
        "/projects/PROJ-ALPHA/schedule/upload",
        files={"file": ("01_baseline_schedule.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert res.status_code == 200
    import_stats = res.json()
    assert import_stats["activities_imported"] > 0

    # 6. Upload text report
    report_content = b"24P201 spool erection started near Rack B. Progress achieved 40%."
    res = client.post(
        "/reports/upload",
        data={"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"},
        files={"file": ("site_daily_report.txt", report_content, "text/plain")}
    )
    assert res.status_code == 201
    report_data = res.json()
    report_id = report_data["report_id"]
    assert report_data["project_id"] == "PROJ-ALPHA"

    # 7. Process report / extract events
    res = client.post(f"/reports/{report_id}/extract")
    assert res.status_code == 200
    proc_data = res.json()
    assert proc_data["processing_status"] in ("COMPLETED", "PROCESSED", "EVENTS_EXTRACTED")
    assert proc_data["event_count"] >= 1

    # 8. Extract event verification
    rep_obj = db_session.query(SourceReport).filter(SourceReport.report_id == report_id).first()
    assert rep_obj is not None
    assert rep_obj.processing_status == "COMPLETED"

    events = db_session.query(ExtractedEvent).filter(ExtractedEvent.report_id == report_id).all()
    assert len(events) >= 1
    event = events[0]
    event_id = event.event_id

    # 9. Verify candidates generated
    res = client.get(f"/events/{event_id}/candidates")
    assert res.status_code == 200
    cand_resp = res.json()
    assert cand_resp["candidate_count"] > 0
    top_cand = cand_resp["candidates"][0]
    act_id = top_cand["activity_id"]

    # 10. Verify decision
    res = client.get(f"/events/{event_id}/decision")
    assert res.status_code == 200
    dec_resp = res.json()
    assert dec_resp["decision"] in [d.value for d in DecisionEnum]

    # 11. Open review queue
    res = client.get("/reviews/pending?project_id=PROJ-ALPHA")
    assert res.status_code == 200
    reviews = res.json()
    assert isinstance(reviews, list)

    # 12. Human review match
    res = client.post(
        f"/reviews/{event_id}/decision",
        json={"decision": "ACCEPT", "selected_activity_id": act_id, "reason": "Approved in E2E test"}
    )
    assert res.status_code == 200
    review_res = res.json()
    assert review_res["applied"] is True

    # 13. Apply progress endpoint check (idempotent)
    res = client.post(f"/events/{event_id}/apply")
    assert res.status_code == 200
    apply_resp = res.json()
    assert apply_resp["applied"] is True

    # 14. Verify schedule updated
    res = client.get("/projects/PROJ-ALPHA/timeline")
    assert res.status_code == 200
    timeline = res.json()
    updated_act = next((a for a in timeline["activities"] if a["activity_id"] == act_id), None)
    assert updated_act is not None
    assert updated_act["status"] in ("STARTED", "IN_PROGRESS", "COMPLETED")

    # 15. Verify audit log
    res = client.get("/audit?project_id=PROJ-ALPHA")
    assert res.status_code == 200
    audits = res.json()
    assert len(audits) >= 1
    assert audits[0]["activity_id"] == act_id

    # 16. Test voice endpoint
    res = client.post(
        "/voice/process",
        json={"transcription_id": "NONEXISTENT", "project_id": "PROJ-ALPHA"}
    )
    # Expected 404 since transcription record does not exist
    assert res.status_code == 404

    # 17. Test invalid project ID (zero silent fallback to PROJ-ALPHA)
    normalized = normalize_project_id("NONEXISTENT_PROJ_9999", db=db_session)
    assert normalized != "PROJ-ALPHA"
    assert "NONEXISTENT_PROJ_9999" in normalized

    # 18. Test invalid state transition: COMPLETED -> STARTED
    act_to_test = db_session.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act_id).first()
    act_to_test.status = "COMPLETED"
    act_to_test.percent_complete = 100.0
    db_session.commit()

    conflicts = detect_schedule_conflicts(
        activity=act_to_test,
        proposed_status="STARTED",
        proposed_percent=10.0,
        proposed_start=None,
        proposed_finish=None
    )
    assert len(conflicts) > 0
    assert any(c["type"] == "STATUS_CONFLICT" for c in conflicts)

    # 19. Test conflict review preservation
    dec = db_session.query(MatchDecision).filter(MatchDecision.event_id == event_id).first()
    dec.decision = DecisionEnum.CONFLICT_REVIEW.value
    db_session.commit()

    dec_service = DecisionService(db_session)
    _, returned_dec = dec_service.make_decision_for_event(event_id)
    assert returned_dec.decision == DecisionEnum.CONFLICT_REVIEW.value

    # 20. Test API error handling
    res = client.get("/projects/DOES-NOT-EXIST")
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()
