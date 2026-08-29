# PragatiSetu — Field Report Ingestion & Schedule Alignment Engine

> **IMPORTANT DISCLAIMER**: The dataset supplied and used in this project is entirely **SYNTHETIC** development/evaluation ground truth. It is **NOT** real Oil India Limited data.

PragatiSetu bridges structured project baseline schedules with field/site progress reports. This repository provides a standalone, clean, modular, and local-first FastAPI backend with a complete REST API contract and local speech-to-text voice input integration.

---

## 🛠️ Technology Stack
- **Language**: Python 3.10+
- **API Framework**: FastAPI, Pydantic v2
- **Database**: PostgreSQL (Production/Docker), SQLite (Local standalone option), SQLAlchemy ORM
- **Migrations**: Alembic (`001` through `007_add_transcriptions`)
- **Speech-to-Text**: `faster-whisper` / `whisper` (`tiny`/`base` loaded once on CPU with singleton model caching)
- **Data Engineering**: Pandas, Openpyxl
- **Event Extraction & Normalization**: Lightweight Rule-Based Engine & Dictionary Mapper (`05_activity_terminology_dictionary.xlsx`, `06_identifier_normalization_dictionary.xlsx`)
- **Fuzzy & Semantic Matching**: RapidFuzz string similarity & SentenceTransformers (`all-MiniLM-L6-v2` loaded once on CPU with cached embeddings)
- **Safety Routing Engine**: Deterministic 85/70/12 threshold policy router (`AUTO_LINK`, `HUMAN_REVIEW`, `UNPLANNED_REVIEW`, `IGNORE`)
- **Human Planner Review**: Controlled human override API (`ACCEPT`, `SWITCH`, `REJECT`, `UNPLANNED`)
- **State Validation & Progress Engine**: Atomic schedule actuals updater, conflict detector, and immutable JSON-snapshot audit trail logger
- **Security & Integrity**: SHA-256 file hashing & path-traversal sanitization
- **Testing**: Pytest (158 automated test cases)

---

## 📁 Repository Structure

```
PragatiSetu/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── projects.py             # Baseline schedule & activity APIs
│   │   │   ├── reports.py              # Report upload & retrieval APIs
│   │   │   ├── events.py               # Event extraction & matching APIs
│   │   │   ├── candidates.py           # Event normalization & candidate generation APIs
│   │   │   ├── decisions.py            # Safety decision routing & explanation APIs
│   │   │   ├── apply.py                # Schedule progress update & audit APIs
│   │   │   ├── reviews.py              # Human review decision APIs
│   │   │   ├── dashboard.py            # Real database metrics dashboard API
│   │   │   ├── timeline.py             # Gantt timeline data API
│   │   │   ├── audit.py                # Global/filtered audit log query API
│   │   │   ├── voice.py                # Spoken voice audio STT & transcript processing APIs
│   │   │   └── placeholders.py         # System metrics & contract APIs
│   │   ├── db/
│   │   │   ├── models/                 # Project, WBSNode, ScheduleActivity, SourceReport, ExtractedEvent, MatchCandidate, MatchDecision, AuditRecord, Transcription
│   │   │   └── database.py             # SQLAlchemy engine & session dependency
│   │   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── services/
│   │   │   ├── baseline_importer.py    # Baseline schedule Excel importer
│   │   │   ├── file_validator.py       # Format, size, schema & discipline validator
│   │   │   ├── audio_validator.py      # Audio format, size limit & filename sanitization validator
│   │   │   ├── hash_service.py         # SHA-256 hash service
│   │   │   ├── storage_service.py      # Local disk storage & sanitization
│   │   │   ├── text_segmenter.py       # Multi-event text segmentation service
│   │   │   ├── field_extractors.py     # Regex field extractors
│   │   │   ├── report_ingestion_service.py # Report ingestion orchestrator
│   │   │   ├── event_extraction_service.py # Event extraction engine
│   │   │   ├── normalizer_service.py   # Identifier, terminology & location normalizer
│   │   │   ├── embedding_service.py    # SentenceTransformers embedding manager & cache
│   │   │   ├── transcription_service.py# Singleton local CPU-first Whisper STT service
│   │   │   ├── voice_service.py        # Voice transcription & pipeline integration service
│   │   │   ├── candidate_scorer.py     # 8-component evidence scorer & weighted heuristic model
│   │   │   ├── candidate_generator_service.py # Candidate shortlist generator & ranker
│   │   │   ├── evidence_service.py     # Evidence completeness calculator & reason builder
│   │   │   ├── decision_policy.py      # Safety threshold policy router (85/70/12)
│   │   │   ├── decision_service.py     # Safety decision orchestrator
│   │   │   ├── state_validator.py      # Status transition & date order validator
│   │   │   ├── conflict_service.py     # Conflict detection engine
│   │   │   ├── audit_service.py        # Immutable audit trail builder
│   │   │   ├── progress_update_service.py # Atomic schedule progress update service
│   │   │   ├── dashboard_service.py    # Real database counts dashboard service
│   │   │   ├── human_review_service.py # Human review decision service
│   │   │   └── timeline_service.py     # Timeline Gantt data service
│   │   ├── config.py                   # Environment settings
│   │   └── main.py                     # FastAPI app entrypoint, CORS & error handlers
│   ├── alembic/                        # Alembic database migrations (001 through 007_add_transcriptions)
│   ├── tests/                          # Pytest test suite (158 tests)
│   ├── alembic.ini                     # Alembic configuration
│   └── requirements.txt                # Lightweight dependencies
├── dataset/                            # Synthetic evaluation package (10 files)
├── uploads/                            # Safe local storage directory for uploaded reports & audio (.gitignore)
├── scripts/
│   ├── generate_synthetic_dataset.py  # Dataset generator
│   ├── inspect_datasets.py            # Programmatic dataset inspector
│   ├── import_baseline.py             # Baseline schedule importer
│   ├── evaluate_extraction.py         # Event extraction evaluation script
│   ├── evaluate_resolver.py           # Candidate generation evaluation script
│   └── evaluate_decisions.py          # Decision routing evaluation script
├── docs/
│   ├── ARCHITECTURE.md                 # System architecture overview
│   ├── REPORT_INGESTION.md             # Report ingestion & validation specification
│   ├── EVENT_EXTRACTION.md             # Event extraction specification
│   ├── RESOLVER.md                     # Event normalization & candidate generation specification
│   ├── DECISION_POLICY.md             # Safety decision routing policy specification
│   ├── STATE_PROGRESS_AUDIT.md        # State progress update & audit trail specification
│   ├── FRONTEND_API_CONTRACT.md       # Frontend developer REST API specification
│   ├── VOICE.md                        # Local CPU-first Speech-to-Text STT specification
│   └── API.md                          # REST API documentation summary
├── Dockerfile                          # Standalone Backend Dockerfile
├── docker-compose.yml                  # Docker Compose setup (Backend + PostgreSQL)
└── README.md
```

---

## 🚀 Quickstart Guide

### Option 1: Native Python Setup

1. **Install Dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Run Database Migrations**:
   ```bash
   python -m alembic -c backend/alembic.ini upgrade head
   ```

3. **Import Project Alpha Baseline Schedule (75 Activities)**:
   ```bash
   python scripts/import_baseline.py
   ```

4. **Start FastAPI Application Server**:
   ```bash
   uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   Open Swagger API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

5. **Run Pytest Test Suite (158 Tests including Full Integration & Voice Tests)**:
   ```bash
   python -m pytest backend/tests -v
   ```

---

## 🎯 Completed Scope 

- [x] Product Naming: **PragatiSetu**
- [x] Standalone FastAPI REST API architecture with CORS & standardized error handlers
- [x] SQLAlchemy ORM models (`Project`, `WBSNode`, `ScheduleActivity`, `SourceReport`, `ExtractedEvent`, `MatchCandidate`, `MatchDecision`, `AuditRecord`, `Transcription`)
- [x] Alembic migrations (`001_initial_schema` through `007_add_transcriptions`)
- [x] Multi-Format Field Report Ingestor (`TXT`, `CSV`, `XLSX`) with SHA-256 duplicate detection
- [x] Local CPU-First Speech-To-Text Transcribe Engine (`faster-whisper` / `whisper` `tiny`/`base` model loaded once on startup)
- [x] Spoken Voice Audio Ingestion API (`POST /voice/transcribe`, `PATCH /transcriptions/{id}`, `POST /voice/process`)
- [x] Multi-Event Segmentation & Extraction Engine
- [x] Event Normalization Engine (`normalizer_service.py` using dataset dictionaries)
- [x] Candidate Generator & 8 Component Evidence Signals (`identifier`, `discipline`, `location`, `action`, `fuzzy`, `semantic`, `temporal`, `dependency`)
- [x] SentenceTransformers Embedding Manager with in-memory schedule activity vector caching
- [x] Safety Decision Policy Router (85/70/12 thresholds) with controlled enum (`AUTO_LINK`, `HUMAN_REVIEW`, `UNPLANNED_REVIEW`, `IGNORE`)
- [x] Human Planner Review API (`ACCEPT`, `SWITCH`, `REJECT`, `UNPLANNED`)
- [x] Atomic Schedule Actuals Progress Updater with Conflict Detector, Immutability Guarantee for Planned Dates, and Immutable Audit Trail Logger
- [x] Real Database Dashboard Summary Metrics API (`GET /projects/{id}/dashboard`)
- [x] Gantt Timeline Data API (`GET /projects/{id}/timeline`)
- [x] Global & Filtered Audit Trail Query API (`GET /audit`)
- [x] Standardized API Contract documentation for Frontend Developers (`docs/FRONTEND_API_CONTRACT.md`) and STT documentation (`docs/VOICE.md`)
- [x] 100% Passing Pytest test suite (158 automated test cases including full end-to-end integration & voice STT tests)
- [x] Dockerfile & docker-compose configuration
