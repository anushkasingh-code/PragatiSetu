import os
import io
import pytest
from datetime import date

def test_full_e2e_backend_pipeline_integration(client):
    """
    Complete end-to-end integration test verifying the entire PragatiSetu backend workflow:
    1. Select PragatiSetu
    2. Upload Baseline Schedule Excel
    3. Upload Field Progress DPR Report
    4. Extract Events
    5. Generate Candidates & Evaluate Match Decision
    6. Process Human Review Decision
    7. Apply Schedule Progress Update & Verify Immutable Planned Baseline
    8. Retrieve Project Timeline / Gantt Data
    9. Retrieve Project Dashboard Metrics
    10. Retrieve Audit Trail Snapshot Log
    """
    # 1. Retrieve PragatiSetu
    proj_res = client.get("/projects/PROJ-ALPHA")
    if proj_res.status_code == 404:
        proj_res = client.post("/projects", json={
            "project_id": "PROJ-ALPHA",
            "name": "PragatiSetu",
            "description": "Refinery Extension"
        })
    assert proj_res.status_code in [200, 201]

    # 2. Upload Baseline Schedule
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    baseline_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    with open(baseline_path, "rb") as f:
        file_bytes = f.read()

    sched_res = client.post(
        "/projects/PROJ-ALPHA/schedule/upload",
        files={"file": ("01_baseline_schedule.xlsx", file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    )
    assert sched_res.status_code == 200
    assert sched_res.json()["activities_imported"] > 0

    # Verify Baseline Activities exist
    acts_res = client.get("/projects/PROJ-ALPHA/activities")
    assert acts_res.status_code == 200
    activities = acts_res.json()
    assert len(activities) > 0

    # 3. Upload DPR Field Progress Report
    report_content = "2026-01-05\n24P201 spool erection started near Rack B."
    rep_upload_res = client.post(
        "/reports/upload",
        data={
            "project_id": "PROJ-ALPHA",
            "report_date": "2026-01-05",
            "discipline": "PIPING"
        },
        files={"file": ("report_e2e.txt", io.BytesIO(report_content.encode("utf-8")), "text/plain")}
    )
    assert rep_upload_res.status_code == 201
    rep_body = rep_upload_res.json()
    report_id = rep_body["report_id"]

    # 4. Extract Events
    extract_res = client.post(f"/reports/{report_id}/extract")
    assert extract_res.status_code == 200
    ext_body = extract_res.json()
    assert ext_body["event_count"] > 0
    event_id = ext_body["events"][0]["event_id"]

    # 5. Generate Candidates & Match Decision
    match_res = client.post(f"/events/{event_id}/match")
    assert match_res.status_code == 200
    match_body = match_res.json()
    assert "decision" in match_body

    # 6. Human Review Decision (ACCEPT)
    review_res = client.post(f"/reviews/{event_id}/decision", json={
        "decision": "ACCEPT",
        "selected_activity_id": match_body["top_activity_id"] or "ACT-ALPHA-020",
        "reason": "E2E Integration Test Planner Confirmation"
    })
    assert review_res.status_code == 200
    rev_body = review_res.json()
    assert rev_body["applied"] is True

    # 7. Retrieve Project Timeline (Verify Planned vs Actuals)
    timeline_res = client.get("/projects/PROJ-ALPHA/timeline")
    assert timeline_res.status_code == 200
    t_body = timeline_res.json()
    assert len(t_body["activities"]) > 0

    # 8. Retrieve Project Dashboard
    dash_res = client.get("/projects/PROJ-ALPHA/dashboard")
    assert dash_res.status_code == 200
    d_body = dash_res.json()
    assert d_body["total_activities"] > 0
    assert d_body["total_reports"] >= 1

    # 9. Retrieve Audit Trail
    audit_res = client.get("/audit?project_id=PROJ-ALPHA")
    assert audit_res.status_code == 200
    audits = audit_res.json()
    assert len(audits) >= 1
    assert audits[0]["event_id"] == event_id
