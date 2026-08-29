import os
import pytest
import io
import pandas as pd
from datetime import date
from backend.app.services.text_segmenter import segment_text_into_events
from backend.app.services.field_extractors import (
    extract_status,
    extract_percent_complete,
    extract_identifier,
    extract_action,
    extract_object,
    extract_location,
    extract_quantity_and_unit
)
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.db.models.report import SourceReport, ProcessingStatus
from backend.app.db.models.event import ExtractedEvent

@pytest.fixture(autouse=True)
def setup_data(db_session):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    if os.path.exists(dataset_path):
        importer = BaselineImporter(db_session)
        importer.import_excel_baseline(dataset_path)

def create_test_report(client, project_id="PROJ-ALPHA", filename="test_report.txt", content=b"Default content", date_str="2026-01-05", discipline="Civil"):
    files = {"file": (filename, content, "text/plain")}
    data = {"project_id": project_id, "report_date": date_str, "discipline": discipline}
    res = client.post("/reports/upload", files=files, data=data)
    assert res.status_code == 201
    return res.json()["report_id"]

def test_1_one_event_txt(client):
    rep_id = create_test_report(client, filename="single.txt", content=b"24P201 spool erection commenced near Rack B.")
    res = client.post(f"/reports/{rep_id}/extract-events")
    assert res.status_code == 200
    events = res.json()["events"]
    assert len(events) == 1
    assert events[0]["identifier"] == "24P201"
    assert events[0]["status"] == "STARTED"

def test_2_multi_event_txt(client):
    content = b"24P201 spool erection commenced near Rack B. Cable tray support installation reached 60% in Rack C."
    rep_id = create_test_report(client, filename="multi.txt", content=content)
    res = client.post(f"/reports/{rep_id}/extract-events")
    assert res.status_code == 200
    events = res.json()["events"]
    assert len(events) == 2
    assert events[0]["identifier"] == "24P201"
    assert events[1]["percent_complete"] == 60.0

def test_3_one_event_csv(client):
    csv_bytes = b"dpr_id,project_id,date,author,summary\nDPR-001,PROJ-ALPHA,2026-01-05,John,Civil excavation finished at Plot A"
    files = {"file": ("dpr.csv", csv_bytes, "text/csv")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05", "discipline": "Civil"}
    up_res = client.post("/reports/upload", files=files, data=data)
    rep_id = up_res.json()["report_id"]

    res = client.post(f"/reports/{rep_id}/extract-events")
    assert res.status_code == 200
    events = res.json()["events"]
    assert len(events) >= 1
    assert events[0]["status"] == "COMPLETED"

def test_4_structured_xlsx(client):
    df = pd.DataFrame([{"dpr_id": "DPR-002", "project_id": "PROJ-ALPHA", "date": "2026-01-06", "summary": "Hydrotesting completed for LINE-ALPHA-201"}])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="DPR_List", index=False)
    
    files = {"file": ("dpr.xlsx", output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-06", "discipline": "Piping"}
    rep_id = client.post("/reports/upload", files=files, data=data).json()["report_id"]

    res = client.post(f"/reports/{rep_id}/extract-events")
    assert res.status_code == 200
    events = res.json()["events"]
    assert len(events) == 1
    assert events[0]["status"] == "COMPLETED"
    assert events[0]["identifier"] == "LINE-ALPHA-201"

def test_5_multiple_events_in_one_sentence(client):
    content = b"F12 reinforcement completed and 24P201 spool erection started near Rack B."
    rep_id = create_test_report(client, filename="single_sentence_multi.txt", content=content)
    res = client.post(f"/reports/{rep_id}/extract-events")
    assert res.status_code == 200
    events = res.json()["events"]
    assert len(events) == 2

def test_6_multiple_events_across_sentences(client):
    content = b"Item 1: Concrete pouring started at Plot A.\nItem 2: Pump alignment completed at Substation 3."
    rep_id = create_test_report(client, filename="multi_sentence.txt", content=content)
    res = client.post(f"/reports/{rep_id}/extract-events")
    assert res.status_code == 200
    assert len(res.json()["events"]) == 2

def test_7_status_started():
    assert extract_status("Work commenced on site") == "STARTED"
    assert extract_status("Excavation started today") == "STARTED"
    assert extract_status("Erection began near Rack A") == "STARTED"

def test_8_status_in_progress():
    assert extract_status("Cable pulling is ongoing") == "IN_PROGRESS"
    assert extract_status("Work is in progress at Plot B") == "IN_PROGRESS"
    assert extract_status("Concreting continued today") == "IN_PROGRESS"

def test_9_status_completed():
    assert extract_status("Hydrotesting completed successfully") == "COMPLETED"
    assert extract_status("Pump alignment is finished") == "COMPLETED"
    assert extract_status("Shuttering done for F12") == "COMPLETED"

def test_10_explicit_percentage():
    assert extract_percent_complete("Work reached 60% completion") == 60.0
    assert extract_percent_complete("Progress is 75.5 percent") == 75.5
    assert extract_percent_complete("90 per cent done") == 90.0

def test_11_invalid_percentage_validation():
    assert extract_percent_complete("Progress is 150%") is None
    assert extract_percent_complete("Work is progressing well") is None

def test_12_identifier_extraction():
    assert extract_identifier("Erection of 24P201 near Rack B") == "24P201"
    assert extract_identifier("Worked on EQ-ALPHA-101 pump") == "EQ-ALPHA-101"
    assert extract_identifier("Concreting for F12 foundation") == "F12"

def test_13_location_extraction():
    assert extract_location("Spool erection near Rack B") == "Rack B"
    assert extract_location("Pouring concrete at Plot A") == "Plot A"
    assert extract_location("Installed cable in Compressor Area") == "Compressor Area"

def test_14_action_extraction():
    act1 = extract_action("Hydrostatic testing completed")
    assert act1 and act1.lower() in ["hydrostatic testing", "hydrotesting", "testing"]
    act2 = extract_action("Pump alignment finished")
    assert act2 and act2.lower() in ["pump alignment", "alignment"]
    act3 = extract_action("Cable pulling in progress")
    assert act3 and act3.lower() in ["cable pulling", "pulling"]

def test_15_object_extraction():
    obj1 = extract_object("Erection of piping spool 24P201")
    assert obj1 and obj1.lower() in ["spool", "piping spool", "pipe"]
    obj2 = extract_object("Concreting of foundation F12")
    assert obj2 and obj2.lower() in ["foundation", "footing"]
    obj3 = extract_object("Cable tray support installation")
    assert obj3 and obj3.lower() in ["cable tray", "cable", "support", "tray support"]

def test_16_quantity_extraction():
    qty, unit = extract_quantity_and_unit("Installed 120 meters of cable tray")
    assert qty == 120.0
    assert unit in ["meters", "m"]

def test_17_missing_identifier():
    assert extract_identifier("Concreting works in progress") is None

def test_18_missing_location():
    assert extract_location("Hydrotesting completed for 24P201") is None

def test_19_missing_status():
    assert extract_status("24P201 spool at Rack B") is None

def test_20_inherited_report_date(client, db_session):
    rep_id = create_test_report(client, date_str="2026-01-15", content=b"24P201 spool erection commenced near Rack B.")
    client.post(f"/reports/{rep_id}/extract-events")

    evt = db_session.query(ExtractedEvent).filter(ExtractedEvent.report_id == rep_id).first()
    assert evt is not None
    assert str(evt.event_date) == "2026-01-15"
    assert evt.event_date_source == "REPORT_DATE"

def test_21_explicit_event_date(client, db_session):
    rep_id = create_test_report(client, date_str="2026-01-15", content=b"On 2026-01-10, 24P201 spool erection commenced near Rack B.")
    client.post(f"/reports/{rep_id}/extract-events")

    evt = db_session.query(ExtractedEvent).filter(ExtractedEvent.report_id == rep_id).first()
    assert evt is not None
    assert str(evt.event_date) == "2026-01-10"
    assert evt.event_date_source == "EXPLICIT"

def test_22_original_raw_text_preservation(client, db_session):
    raw_str = "24-P-201 spool erection commenced near Rack-B."
    rep_id = create_test_report(client, content=raw_str.encode("utf-8"))
    client.post(f"/reports/{rep_id}/extract-events")

    evt = db_session.query(ExtractedEvent).filter(ExtractedEvent.report_id == rep_id).first()
    assert evt.raw_text == raw_str

def test_23_source_line_row_preservation(client, db_session):
    rep_id = create_test_report(client, content=b"Line 1: 24P201 erection started.\nLine 2: F12 concreting finished.")
    client.post(f"/reports/{rep_id}/extract-events")

    evts = db_session.query(ExtractedEvent).filter(ExtractedEvent.report_id == rep_id).all()
    assert len(evts) == 2
    assert evts[0].source_position["line"] == 1
    assert evts[1].source_position["line"] == 2

def test_24_extraction_version(client, db_session):
    rep_id = create_test_report(client, content=b"24P201 spool erection commenced near Rack B.")
    client.post(f"/reports/{rep_id}/extract-events")
    evt = db_session.query(ExtractedEvent).filter(ExtractedEvent.report_id == rep_id).first()
    assert evt.extraction_version == "v1"

def test_25_extraction_method(client, db_session):
    rep_id = create_test_report(client, content=b"24P201 spool erection commenced near Rack B.")
    client.post(f"/reports/{rep_id}/extract-events")
    evt = db_session.query(ExtractedEvent).filter(ExtractedEvent.report_id == rep_id).first()
    assert evt.extraction_method == "RULE_BASED"

def test_26_empty_non_event_report(client):
    rep_id = create_test_report(client, content=b"Site safety meeting held today. No work carried out.")
    res = client.post(f"/reports/{rep_id}/extract-events")
    assert res.status_code == 200
    assert len(res.json()["events"]) == 0

def test_27_malformed_stored_content_handling(client, db_session):
    rep = SourceReport(
        report_id="REP-MALFORMED",
        project_id="PROJ-ALPHA",
        filename="corrupt.txt",
        source_type="TXT",
        report_date=date(2026, 1, 5),
        file_hash="dummy123",
        file_size=10,
        stored_path="nonexistent_path.txt",
        raw_content=None,
        processing_status="VALIDATED"
    )
    db_session.add(rep)
    db_session.commit()

    res = client.post("/reports/REP-MALFORMED/extract-events")
    assert res.status_code == 200
    assert len(res.json()["events"]) == 0

def test_28_nonexistent_report(client):
    res = client.post("/reports/NONEXISTENT_REP/extract-events")
    assert res.status_code == 404

def test_29_duplicate_extraction_idempotency(client):
    rep_id = create_test_report(client, content=b"24P201 spool erection commenced near Rack B.")
    
    res1 = client.post(f"/reports/{rep_id}/extract-events")
    assert res1.status_code == 200
    evt_cnt1 = res1.json()["event_count"]

    res2 = client.post(f"/reports/{rep_id}/extract-events")
    assert res2.status_code == 200
    evt_cnt2 = res2.json()["event_count"]
    assert evt_cnt1 == evt_cnt2

def test_30_foreign_key_integrity_and_events_retrieval(client, db_session):
    rep_id = create_test_report(client, content=b"24P201 spool erection commenced near Rack B.")
    client.post(f"/reports/{rep_id}/extract-events")

    # Call GET /reports/{report_id}/events
    res = client.get(f"/reports/{rep_id}/events")
    assert res.status_code == 200
    evts = res.json()
    assert len(evts) >= 1
    assert evts[0]["report_id"] == rep_id
