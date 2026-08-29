# PragatiSetu — Frontend Developer REST API Integration Contract

> **NOTICE**: Synthetic prototype dataset — not real Oil India Limited data.

This document serves as the complete REST API integration specification for frontend developers building UI dashboards or client applications for **PragatiSetu**.

---

## 🌐 Server Base URL & Documentation
- **Default Local Server Base URL**: `http://127.0.0.1:8000`
- **Interactive OpenAPI / Swagger UI**: `http://127.0.0.1:8000/docs`
- **OpenAPI JSON Schema**: `http://127.0.0.1:8000/openapi.json`
- **CORS Support**: Configurable via `CORS_ORIGINS` (defaults to `*` for local dev).

---

## Standardized Error Response Format

All error responses return standard HTTP status codes along with a structured JSON error payload:

```json
{
  "detail": "Descriptive error message",
  "error": {
    "code": "BAD_REQUEST | RESOURCE_NOT_FOUND | RESOURCE_CONFLICT | UNPROCESSABLE_ENTITY | INTERNAL_SERVER_ERROR",
    "message": "Human-readable error explanation",
    "details": {}
  }
}
```

---

## Core API Endpoints

### 1. System Health Check
`GET /health`
- **Response (`200 OK`)**:
  ```json
  {
    "status": "ok",
    "app": "PragatiSetu Backend",
    "environment": "production",
    "database": "connected"
  }
  ```

---

### 2. Projects & Schedules

#### List Projects
`GET /projects`

#### Get Project Details
`GET /projects/{project_id}`

#### Upload Baseline Schedule Excel
`POST /projects/{project_id}/schedule/upload`
- **Content-Type**: `multipart/form-data` (`file`)

#### Get Project WBS Hierarchy
`GET /projects/{project_id}/wbs`

#### Get Project Activities
`GET /projects/{project_id}/activities`
- **Query Params**: `status` (optional), `discipline` (optional)

#### Get Single Activity Details
`GET /activities/{activity_id}`

---

### 3. Report Ingestion

#### Upload Field Report (TXT, CSV, XLSX)
`POST /reports/upload`
- **Content-Type**: `multipart/form-data`
- **Form Fields**: `file` (File), `project_id` (str), `report_date` (YYYY-MM-DD), `discipline` (str)
- **Response (`201 Created`)**: `ReportUploadResponse`
- **Error (`409 Conflict`)**: Duplicate report file hash detected for project.

#### Get Project Reports
`GET /projects/{project_id}/reports`

#### Get Report Details
`GET /reports/{report_id}`

---

### 4. Event Extraction & Matching

#### Extract Events from Report
`POST /reports/{report_id}/extract-events` or `POST /reports/{report_id}/extract`

#### Retrieve Report Extracted Events
`GET /reports/{report_id}/events`

#### Generate Candidate Shortlist & Hybrid Score
`POST /events/{event_id}/candidates`

#### Retrieve Event Candidates
`GET /events/{event_id}/candidates`

#### Evaluate Event Match & Safety Decision
`POST /events/{event_id}/decision` or `POST /events/{event_id}/match`
- **Response (`200 OK`)**:
  ```json
  {
    "event_id": "EVT-20260615-A1B2C3D4",
    "recommended_decision": "AUTO_LINK | HUMAN_REVIEW | UNPLANNED_REVIEW | IGNORE",
    "best_candidate_activity_id": "ACT-ALPHA-012",
    "best_candidate_score": 92.5,
    "evidence_completeness": 87.5,
    "top_2_margin": 24.0,
    "explanation": {
      "summary": "High confidence match (92.5%) for activity ACT-ALPHA-012.",
      "reasons": ["Identifier exact match", "Action alignment"]
    }
  }
  ```

---

### 5. Human Planner Review & Override

#### Submit Human Review Decision
`POST /reviews/{event_id}/decision`
- **Request Body**:
  ```json
  {
    "planner_action": "ACCEPT | SWITCH | REJECT | UNPLANNED",
    "override_activity_id": "ACT-ALPHA-012",
    "reason": "Verified field supervisor ground report."
  }
  ```

---

### 6. Progress Application & Audit Trail

#### Apply Progress to Schedule
`POST /events/{event_id}/apply`
- **Response (`200 OK`)**:
  ```json
  {
    "success": true,
    "event_id": "EVT-20260615-A1B2C3D4",
    "activity_id": "ACT-ALPHA-012",
    "previous_status": "NOT_STARTED",
    "new_status": "STARTED",
    "previous_percentage": 0.0,
    "new_percentage": 25.0,
    "actual_start": "2026-06-15",
    "actual_finish": null,
    "audit_id": "AUD-20260615-9F8E7D6C"
  }
  ```

#### Get Activity Audit Logs
`GET /activities/{activity_id}/audit`

#### Query Global Audit Trail
`GET /audit`

---

### 7. Gantt Timeline & Dashboard Metrics

#### Get Project Timeline Data (Gantt Chart)
`GET /projects/{project_id}/timeline`

#### Get Real Database Dashboard Metrics
`GET /projects/{project_id}/dashboard`

---

### 8. Voice Audio Input (Local STT)

#### Upload & Transcribe Spoken Voice Audio
`POST /voice/transcribe`
- **Content-Type**: `multipart/form-data` (`file`)

#### Edit / Correct Spoken Transcript
`PATCH /transcriptions/{transcription_id}`
- **Request Body**: `{"transcript": "24P201 spool erection started near Rack B."}`

#### Process Voice Transcript to Events
`POST /transcriptions/{transcription_id}/process` or `POST /voice/process`
