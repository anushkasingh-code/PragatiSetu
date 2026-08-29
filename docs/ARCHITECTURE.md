# PragatiSetu — Backend Architecture Specification

> **NOTICE**: Synthetic prototype dataset — not real Oil India Limited data.

## System Conceptual Architecture

PragatiSetu bridges structured project baseline schedules with field reports.

```
BASELINE SCHEDULE
        ↓
FIELD INPUT (DPR / TXT / CSV / XLSX)  or  VOICE AUDIO (.wav, .mp3, .m4a, .webm, .ogg) [Milestone 8 Local STT]
        ↓                                           ↓
        └─────────────────► TRANSCRIPT ──────────────┘
                                  ↓
REPORT VALIDATION & SHA-256 DUPLICATE CHECK [Milestone 2]
                                  ↓
EVENT EXTRACTION & MULTI-EVENT SEGMENTATION [Milestone 3]
                                  ↓
NORMALIZATION & DICTIONARY MAPPING [Milestone 4]
                                  ↓
CANDIDATE GENERATION & PRECOMPUTED EMBEDDINGS [Milestone 4]
                                  ↓
8-COMPONENT EVIDENCE SCORES & RANKING [Milestone 4]
                                  ↓
SAFETY & DECISION LAYER (85/70/12 Threshold Engine) [Milestone 5]
                                  ↓
HUMAN PLANNER REVIEW (ACCEPT / SWITCH / REJECT / UNPLANNED) [Milestone 7]
                                  ↓
STATE VALIDATION & CONFLICT CHECK [Milestone 6]
                                  ↓
ACTUAL PROGRESS UPDATE & ATOMIC COMMIT [Milestone 6]
                                  ↓
IMMUTABLE AUDIT RECORD [Milestone 6]
                                  ↓
TIMELINE / GANTT & DASHBOARD APIS [Milestone 7 Backend REST Contract]
```

## Completed Architecture Scope (Milestones 1–8)

1. **FastAPI Web Framework** (`backend/app/main.py`) with global structured JSON exception handlers and configurable CORS middleware.
2. **SQLAlchemy ORM Data Models** (`Project`, `WBSNode`, `ScheduleActivity`, `SourceReport`, `ExtractedEvent`, `MatchCandidate`, `MatchDecision`, `AuditRecord`, `Transcription`)
3. **Database Migration Framework** (`Alembic` revisions 001, 002, 003, 004, 005, 006, 007)
4. **Baseline Schedule Importer** (`backend/app/services/baseline_importer.py`)
5. **Report Ingestion Pipeline & SHA-256 Duplicate Detector** (`backend/app/services/report_ingestion_service.py`)
6. **Multi-Event Extraction Engine** (`backend/app/services/event_extraction_service.py`)
7. **Event Normalization Engine** (`backend/app/services/normalizer_service.py`)
8. **Candidate Scorer & Embedding Service** (`backend/app/services/candidate_scorer.py`, `backend/app/services/embedding_service.py`)
9. **Candidate Generator Service** (`backend/app/services/candidate_generator_service.py`)
10. **Safety Decision Service & Evidence Service** (`backend/app/services/decision_service.py`, `backend/app/services/evidence_service.py`, `backend/app/services/decision_policy.py`)
11. **Human Review Service** (`backend/app/services/human_review_service.py`)
12. **State Validation & Conflict Service** (`backend/app/services/state_validator.py`, `backend/app/services/conflict_service.py`)
13. **Progress Update Service & Audit Service** (`backend/app/services/progress_update_service.py`, `backend/app/services/audit_service.py`)
14. **Dashboard & Timeline Services** (`backend/app/services/dashboard_service.py`, `backend/app/services/timeline_service.py`)
15. **Local CPU-First Speech-To-Text Engine** (`backend/app/services/transcription_service.py`, `backend/app/services/voice_service.py`, `backend/app/services/audio_validator.py`)
16. **Complete REST API Endpoints** (`/health`, `/projects`, `/activities`, `/reports`, `/events/{id}/extract`, `/events/{id}/candidates`, `/events/{id}/match`, `/events/{id}/apply`, `/reviews/{id}/decision`, `/projects/{id}/timeline`, `/projects/{id}/dashboard`, `/audit`, `/voice/transcribe`, `/transcriptions/{id}`, `/voice/process`, `/metrics`)
17. **Comprehensive Pytest Suite** (`backend/tests/` - 158 automated test cases including contract, voice, and full integration tests)
18. **Containerization** (`Dockerfile`, `docker-compose.yml`)

## Core Principles
- **Voice as Input Modality**: Spoken audio is transcribed locally and passed into the exact same text processing pipeline.
- **Immutable Planned Schedule Baseline**: Planned schedule dates (`planned_start`, `planned_finish`) are **NEVER** modified.
- **Zero Hardcoded Demo Data**: All counts, scores, timeline dates, and progress states are calculated dynamically from actual database queries.
- **Atomic Transactions & Audit Traceability**: Schedule update, audit creation, and event status update commit atomically with complete rollback.
- **Local-First & Offline Capable**: Runs on CPU across Windows, macOS, and Linux using PostgreSQL or SQLite.
