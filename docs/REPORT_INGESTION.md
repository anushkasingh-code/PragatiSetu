# PragatiSetu — Report Ingestion & Validation Specification

> **IMPORTANT NOTICE**: The dataset supplied and processed in this project is entirely **SYNTHETIC** development/evaluation ground truth. It is **NOT** real Oil India Limited data.

---

## 1. Overview
The Report Ingestion module in **PragatiSetu** handles incoming field progress reports (`TXT`, `CSV`, `XLSX`). It validates input files prior to AI event extraction, calculates deterministic SHA-256 hashes, prevents duplicate file submissions, stores raw content safely on disk, and records `SourceReport` database entries.

---

## 2. Ingestion Pipeline Workflow

```
FIELD REPORT (TXT / CSV / XLSX)
        ↓
POST /reports/upload (FastAPI UploadFile)
        ↓
PROJECT EXISTENCE CHECK (DB Query)
        ↓
FILE EXTENSION & SIZE VALIDATION (.txt, .csv, .xlsx <= 10MB)
        ↓
CONTENT & SCHEMA VALIDATION (Non-empty, required columns, valid discipline & date)
        ↓
DETERMINISTIC SHA-256 HASH COMPUTATION
        ↓
DUPLICATE FILE CHECK (file_hash + project_id in DB)
  ├── IF DUPLICATE: Return 200 OK with duplicate: true & existing report_id (No new DB row created)
  └── IF UNIQUE:
        ↓
SAFE DISK STORAGE (pathlib sanitization under UPLOAD_DIR)
        ↓
STORE SourceReport (processing_status = "VALIDATED")
```

---

## 3. Supported Formats & Discovered Spreadsheet Schemas

### Supported Formats
- `.txt` (UTF-8 / Latin-1 encoded raw text reports)
- `.csv` (Comma-separated values with data header)
- `.xlsx` (Excel workbooks containing readable sheets)

### Discovered Required Spreadsheet Columns
From inspecting the synthetic dataset package (`03_daily_progress_reports.xlsx` & `04_discipline_progress_reports.xlsx`):

1. **Daily Progress Reports (DPR)**:
   - Required Columns: `dpr_id`, `project_id`, `date`
2. **Discipline Progress Reports**:
   - Required Columns: `report_id`, `project_id`, `discipline`

---

## 4. Controlled Processing Statuses
- `PENDING`: Initial state during async queueing (if applicable).
- `VALIDATED`: Successfully validated and stored report ready for event extraction.
- `REJECTED`: Validation failure (empty content, unsupported format, invalid project/date/discipline).
- `PROCESSED`: Completed event extraction and matching (Future Milestones).

---

## 5. Machine-Readable Validation Error Codes

| Error Code | HTTP Status | Description |
| --- | --- | --- |
| `UNSUPPORTED_FILE_TYPE` | `400 Bad Request` | File extension is not `.txt`, `.csv`, or `.xlsx`. |
| `FILE_TOO_LARGE` | `400 Bad Request` | File size exceeds `MAX_FILE_SIZE_BYTES` (10 MB). |
| `EMPTY_FILE` | `400 Bad Request` | 0-byte file, whitespace-only text, or empty sheet/table. |
| `MALFORMED_FILE` | `400 Bad Request` | Corrupt zip/excel file or unparseable text/csv. |
| `INVALID_PROJECT` | `404 Not Found` | Specified `project_id` does not exist in `projects` table. |
| `INVALID_REPORT_DATE` | `400 Bad Request` | Unparseable report date string. |
| `INVALID_DISCIPLINE` | `400 Bad Request` | Unknown discipline (Must be one of: `Civil`, `Piping`, `Mechanical`, `Electrical`, `Instrumentation`, `General`). |
| `MISSING_REQUIRED_COLUMNS` | `400 Bad Request` | Spreadsheet missing required headers for DPR or Discipline Report. |
| `DUPLICATE_FILE` | `200 OK` | Identical file hash already ingested for project. |

---

## 6. Example API Requests & Responses

### Successful Report Upload (`POST /reports/upload`)

**Request**:
```http
POST /reports/upload HTTP/1.1
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary

------WebKitFormBoundary
Content-Disposition: form-data; name="project_id"

PROJ-ALPHA
------WebKitFormBoundary
Content-Disposition: form-data; name="report_date"

2026-01-05
------WebKitFormBoundary
Content-Disposition: form-data; name="discipline"

Civil
------WebKitFormBoundary
Content-Disposition: form-data; name="file"; filename="report_civil_day1.txt"
Content-Type: text/plain

Completed 50% excavation for Plot A civil works.
------WebKitFormBoundary--
```

**Response (`201 Created`)**:
```json
{
  "report_id": "REP-20260829-9A3F12BC",
  "project_id": "PROJ-ALPHA",
  "filename": "report_civil_day1.txt",
  "source_type": "TXT",
  "report_date": "2026-01-05",
  "discipline": "Civil",
  "processing_status": "VALIDATED",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "duplicate": false,
  "validation": {
    "valid": true,
    "errors": [],
    "warnings": []
  }
}
```

---

### Duplicate File Response (`POST /reports/upload`)

**Response (`201 Created`)**:
```json
{
  "report_id": "REP-20260829-9A3F12BC",
  "project_id": "PROJ-ALPHA",
  "filename": "report_civil_day1.txt",
  "source_type": "TXT",
  "report_date": "2026-01-05",
  "discipline": "Civil",
  "processing_status": "VALIDATED",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "duplicate": true,
  "validation": {
    "valid": false,
    "errors": [
      {
        "code": "DUPLICATE_FILE",
        "message": "Duplicate report file detected. This exact file content was already uploaded as report 'REP-20260829-9A3F12BC'."
      }
    ],
    "warnings": []
  }
}
```
