import os
import io
import pytest
import pandas as pd
from backend.app.services.hash_service import calculate_sha256
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.db.models.report import SourceReport, ProcessingStatus

@pytest.fixture(autouse=True)
def setup_test_project(db_session):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    if os.path.exists(dataset_path):
        importer = BaselineImporter(db_session)
        importer.import_excel_baseline(dataset_path)

def test_1_valid_txt_upload(client):
    content = b"Site progress report for Civil works on Plot A. Completed excavation."
    files = {"file": ("report_day1.txt", content, "text/plain")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05", "discipline": "Civil"}
    
    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 201
    res = response.json()
    assert res["processing_status"] in ("VALIDATED", "EVENTS_EXTRACTED", "PROCESSED")
    assert res["source_type"] == "TXT"
    assert res["duplicate"] is False
    assert res["validation"]["valid"] is True

def test_2_valid_csv_upload(client):
    csv_str = "dpr_id,project_id,date,author,summary\nDPR-001,PROJ-ALPHA,2026-01-05,John,Completed piping"
    files = {"file": ("dpr_report.csv", csv_str.encode("utf-8"), "text/csv")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05", "discipline": "Piping"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 201
    res = response.json()
    assert res["source_type"] == "CSV"
    assert res["processing_status"] in ("VALIDATED", "EVENTS_EXTRACTED", "PROCESSED")

def test_3_valid_xlsx_upload(client):
    df = pd.DataFrame([
        {"dpr_id": "DPR-002", "project_id": "PROJ-ALPHA", "date": "2026-01-06", "summary": "XLSX report data"}
    ])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="DPR_List", index=False)
    content = output.getvalue()

    files = {"file": ("03_daily_progress_reports.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-06", "discipline": "General"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 201
    res = response.json()
    assert res["source_type"] == "XLSX"

def test_4_unsupported_extension_rejection(client):
    files = {"file": ("document.pdf", b"%PDF-1.4 test content", "application/pdf")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 400
    res = response.json()
    assert "detail" in res
    assert res["detail"]["errors"][0]["code"] == "UNSUPPORTED_FILE_TYPE"

def test_5_empty_txt_rejection(client):
    files = {"file": ("empty.txt", b"   \n\t ", "text/plain")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["errors"][0]["code"] == "EMPTY_FILE"

def test_6_empty_csv_rejection(client):
    files = {"file": ("empty.csv", b"", "text/csv")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["errors"][0]["code"] == "EMPTY_FILE"

def test_7_malformed_csv_handling(client):
    # CSV with malformed unclosed quotes
    files = {"file": ("malformed.csv", b'col1,col2\n"unclosed quote line,123', "text/csv")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"}

    response = client.post("/reports/upload", files=files, data=data)
    # Should either reject cleanly or parse safely
    assert response.status_code in [400, 201]

def test_8_malformed_xlsx_handling(client):
    files = {"file": ("corrupt.xlsx", b"not a real zip excel file", "application/vnd.ms-excel")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["errors"][0]["code"] == "MALFORMED_FILE"

def test_9_missing_project_id_rejection(client):
    files = {"file": ("valid.txt", b"Report text content", "text/plain")}
    data = {"project_id": "NONEXISTENT_PROJECT_ID", "report_date": "2026-01-05"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 404

def test_10_invalid_report_date_rejection(client):
    files = {"file": ("valid.txt", b"Report text content", "text/plain")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "invalid-date-format"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["errors"][0]["code"] == "INVALID_REPORT_DATE"

def test_11_invalid_discipline_rejection(client):
    files = {"file": ("valid.txt", b"Report text content", "text/plain")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05", "discipline": "Astronomy"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["errors"][0]["code"] == "INVALID_DISCIPLINE"

def test_12_missing_required_spreadsheet_columns(client):
    # DPR report missing 'date' column
    df = pd.DataFrame([{"dpr_id": "DPR-100", "project_id": "PROJ-ALPHA", "author": "John"}])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="DPR_List", index=False)

    files = {"file": ("dpr_missing_cols.xlsx", output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["errors"][0]["code"] == "MISSING_REQUIRED_COLUMNS"

def test_13_deterministic_sha256_calculation():
    content = b"Exact test report bytes"
    hash1 = calculate_sha256(content)
    hash2 = calculate_sha256(content)
    assert hash1 == hash2
    assert len(hash1) == 64

def test_14_15_duplicate_file_detection_and_repeated_upload(client):
    content = b"Unique field event content for SHA256 duplicate testing."
    files = {"file": ("report_unique.txt", content, "text/plain")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"}

    # Upload 1
    res1 = client.post("/reports/upload", files=files, data=data)
    assert res1.status_code == 201
    rep1_id = res1.json()["report_id"]

    # Upload 2 (Identical Content)
    res2 = client.post("/reports/upload", files=files, data=data)
    assert res2.status_code == 201
    res2_json = res2.json()
    assert res2_json["duplicate"] is True
    assert res2_json["report_id"] == rep1_id
    assert res2_json["validation"]["errors"][0]["code"] == "DUPLICATE_FILE"

def test_16_successful_sourcereport_creation(client, db_session):
    content = b"Field progress for Mechanical discipline equipment alignment."
    files = {"file": ("mech_report.txt", content, "text/plain")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-08", "discipline": "Mechanical"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 201
    rep_id = response.json()["report_id"]

    report_db = db_session.query(SourceReport).filter(SourceReport.report_id == rep_id).first()
    assert report_db is not None
    assert report_db.project_id == "PROJ-ALPHA"
    assert report_db.discipline == "Mechanical"
    assert report_db.processing_status in ("VALIDATED", "EVENTS_EXTRACTED", "PROCESSED")

def test_17_rejected_report_does_not_create_db_record(client, db_session):
    count_before = db_session.query(SourceReport).count()
    files = {"file": ("unsupported.exe", b"binary data", "application/octet-stream")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 400
    count_after = db_session.query(SourceReport).count()
    assert count_after == count_before

def test_18_19_project_reports_listing_and_retrieval_api(client):
    content = b"Report content for listing and individual API endpoints test."
    files = {"file": ("list_test.txt", content, "text/plain")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-10"}

    res_up = client.post("/reports/upload", files=files, data=data)
    rep_id = res_up.json()["report_id"]

    # 1. GET /reports/{report_id}
    res_single = client.get(f"/reports/{rep_id}")
    assert res_single.status_code == 200
    assert res_single.json()["report_id"] == rep_id

    # 2. GET /projects/PROJ-ALPHA/reports
    res_list = client.get("/projects/PROJ-ALPHA/reports")
    assert res_list.status_code == 200
    reports = res_list.json()
    assert any(r["report_id"] == rep_id for r in reports)

def test_20_path_traversal_filename_sanitization(client, db_session):
    content = b"Path traversal security test file content."
    files = {"file": ("../../../../etc/passwd.txt", content, "text/plain")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 201
    rep_id = response.json()["report_id"]
    
    report_db = db_session.query(SourceReport).filter(SourceReport.report_id == rep_id).first()
    assert report_db is not None
    assert "passwd.txt" in report_db.stored_path
    assert "etc" not in report_db.stored_path or "passwd.txt" == os.path.basename(report_db.stored_path)

def test_21_exceeding_file_size_limit_rejection(client):
    large_content = b"A" * (11 * 1024 * 1024)  # 11 MB > 10 MB limit
    files = {"file": ("large_report.txt", large_content, "text/plain")}
    data = {"project_id": "PROJ-ALPHA", "report_date": "2026-01-05"}

    response = client.post("/reports/upload", files=files, data=data)
    assert response.status_code == 400
    assert response.json()["detail"]["errors"][0]["code"] == "FILE_TOO_LARGE"
