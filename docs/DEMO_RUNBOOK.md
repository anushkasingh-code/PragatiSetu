# PragatiSetu — SIH Live Demonstration Runbook

> **IMPORTANT DISCLAIMER**: The dataset supplied and used in this demonstration is entirely **SYNTHETIC** development/evaluation ground truth. It is **NOT** real Oil India Limited data.

This runbook documents the step-by-step procedure to execute an end-to-end live demonstration of **PragatiSetu** for the Smart India Hackathon (SIH) jury or stakeholders.

---

## 🚀 Step 1: Environment & Database Startup

### Option A: Local Python + SQLite / PostgreSQL
```bash
# 1. Install dependencies
pip install -r backend/requirements.txt

# 2. Run Alembic database migrations
python -m alembic -c backend/alembic.ini upgrade head

# 3. Seed / Import Project Alpha Baseline Schedule (75 Activities)
python scripts/import_baseline.py

# 4. Launch FastAPI Application Server
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Option B: Docker Compose (PostgreSQL + FastAPI)
```bash
docker-compose up --build
```

Access Interactive Swagger Documentation: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

## 📋 Step 2: System Health Verification
`GET http://127.0.0.1:8000/health`

**Expected Response (`200 OK`)**:
```json
{
  "status": "ok",
  "app": "PragatiSetu Backend",
  "environment": "production",
  "database": "connected"
}
```

---

## 📊 Step 3: Baseline Project Schedule Inspection
`GET http://127.0.0.1:8000/projects/PROJ-ALPHA`

**Expected Response**: Returns project metadata (`PROJ-ALPHA`, total activities: 75, planned date bounds).

`GET http://127.0.0.1:8000/projects/PROJ-ALPHA/activities`

**Expected Output**: Lists 75 schedule activities with planned dates, zero initial actual dates, and `status: "NOT_STARTED"`.

---

## 📥 Step 4: Daily Progress Report Ingestion (File Upload)
`POST http://127.0.0.1:8000/reports/upload`

**Form Data**:
- `file`: `dataset/02_dpr_sample_2026-06-15.txt`
- `project_id`: `PROJ-ALPHA`
- `report_date`: `2026-06-15`
- `discipline`: `CIVIL`

**Expected Response (`201 Created`)**:
```json
{
  "report_id": "REP-20260615-1A2B3C4D",
  "filename": "02_dpr_sample_2026-06-15.txt",
  "file_hash": "a1b2c3d4...",
  "processing_status": "VALIDATED"
}
```

*Duplicate Upload Protection*: Uploading the exact same report file again immediately returns HTTP `409 Conflict` (Duplicate report detected).

---

## 🔍 Step 5: Multi-Event Extraction
`POST http://127.0.0.1:8000/reports/{report_id}/extract-events`

**Expected Output**: Segments report text into distinct events, extracting action, object, identifier, location, status, percentage, and provenance.

---

## 🤖 Step 6: Candidate Matching & Hybrid Scoring
`POST http://127.0.0.1:8000/events/{event_id}/decision`

**Expected Output**:
1. Normalizes identifier and terminology using dataset dictionaries.
2. Generates candidate shortlist with precomputed SentenceTransformers embeddings and RapidFuzz string matching.
3. Computes 8-component evidence scores (identifier, discipline, location, action, fuzzy, semantic, temporal, dependency).
4. Routes event through safety policy router (`85.0` match score, `70.0` evidence completeness, `12.0` top-2 margin).

---

## 👤 Step 7: Human Planner Review (If Required)
`POST http://127.0.0.1:8000/reviews/{event_id}/decision`

**Request Body**:
```json
{
  "planner_action": "ACCEPT",
  "override_activity_id": "ACT-ALPHA-012",
  "reason": "Verified field supervisor ground report."
}
```

---

## ⚡ Step 8: Atomic Schedule Actuals Progress Update
`POST http://127.0.0.1:8000/events/{event_id}/apply`

**Expected Output**:
- Validates state transition (`NOT_STARTED` $\rightarrow$ `STARTED` / `IN_PROGRESS` / `COMPLETED`).
- Performs conflict detection.
- Atomically updates `ScheduleActivity` actual dates and `percent_complete`.
- Planned dates (`planned_start`, `planned_finish`) remain **100% immutable**.
- Creates immutable JSON snapshot `AuditRecord`.

---

## 📈 Step 9: Gantt Timeline & Dashboard Metrics Inspection
- `GET http://127.0.0.1:8000/projects/PROJ-ALPHA/timeline` (Gantt chart timeline data)
- `GET http://127.0.0.1:8000/projects/PROJ-ALPHA/dashboard` (Real database metrics dashboard)
- `GET http://127.0.0.1:8000/audit` (Global audit log query)

---

## 🎙️ Step 10: Local Voice Input Demonstration (Optional)
`POST http://127.0.0.1:8000/voice/transcribe`

**Form Data**: `file`: `sample_field_voice.wav`
- Transcribes audio locally using CPU-first Whisper `tiny`.
- Returns spoken text transcript.
- `POST http://127.0.0.1:8000/transcriptions/{id}/process`: Submits transcript into existing event extraction pipeline.

---

## 🧪 Step 11: Reproducible Decision Evaluation Engine
```bash
python scripts/evaluate_decisions.py
```

**Expected Output**: Runs quantitative evaluation on synthetic ground truth evaluation pairs, logging accuracy, precision, recall, F1-score, and safety routing distribution.
