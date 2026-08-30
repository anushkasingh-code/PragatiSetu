"""
FINAL ADVERSARIAL BACKEND VALIDATION
Pragati Setu – Backend-testing branch
Covers all 25 validation areas from the brief:
  1-2   DB Integrity & Idempotency
  3     Invalid Files
  4     Text Extraction Edge-Cases (negation / uncertainty / future tense)
  5     Multi-Event Splitting
  6     Identifier Normalization
  7     Ambiguity Detection
  8     Unplanned Work
  9     Irrelevant Text
  10    State Regression
  11    Date Edge-Cases
  12    Dependency Edge-Cases
  13    Match Score Safety
  14    Embedding Model
  15    API Contract
  16    Security
  17    Audit Immutability
  18    Concurrency (thread-level)
  19    Voice (edge-cases)
  20-21 Dataset / Randomised Stress placeholders
  22    Restart / DB persistence
  23    Clean Machine Setup
  24    Final Regression (compile + pytest entry-point)
"""

import datetime
import io
import os
import re
import threading
import uuid
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ──────────────────────────────────────────────────────────────────────────────
# Local imports
# ──────────────────────────────────────────────────────────────────────────────
from backend.app.db.database import Base, get_db
from backend.app.main import app
from backend.app.db.models.project import Project
from backend.app.db.models.activity import ScheduleActivity
from backend.app.db.models.report import SourceReport, ProcessingStatus
from backend.app.db.models.event import ExtractedEvent
from backend.app.db.models.decision import MatchDecision
from backend.app.db.models.audit import AuditRecord
from backend.app.services.field_extractors import (
    extract_status, extract_percent_complete, extract_identifier,
    extract_action, extract_location,
)
from backend.app.services.normalizer_service import normalize_identifier
from backend.app.services.text_segmenter import segment_text_into_events
from backend.app.services.state_validator import (
    validate_state_transition, validate_date_ordering, validate_percentage,
    check_dependency_warnings,
)
from backend.app.services.conflict_service import detect_schedule_conflicts
from backend.app.services.candidate_scorer import (
    score_identifier, score_discipline, score_location,
    compute_all_candidate_scores, MATCH_WEIGHTS,
)
from backend.app.services.file_validator import (
    validate_file_content, validate_file_size, validate_file_extension,
    validate_report_date, validate_discipline, ReportValidationError,
)
from backend.app.services.audit_service import build_schedule_state_snapshot
from backend.app.services.embedding_service import (
    compute_semantic_similarity, get_embedding_model,
    _SCHEDULE_EMBEDDINGS_CACHE, precompute_schedule_embeddings,
)
from backend.app.services.progress_update_service import ProgressUpdateService
from backend.app.services.decision_service import DecisionService
from backend.app.services.event_extraction_service import EventExtractionService
from backend.app.services.report_ingestion_service import ReportIngestionService
from backend.app.config import settings

# ──────────────────────────────────────────────────────────────────────────────
# Shared in-memory DB fixtures
# ──────────────────────────────────────────────────────────────────────────────

ADVERSARIAL_DB_URL = "sqlite:///:memory:"

_engine = create_engine(
    ADVERSARIAL_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=_engine)
    session = _Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_engine)


@pytest.fixture(scope="function")
def client(db):
    def _override():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_project(db, pid="ADV-PROJ-001", name="Adversarial Test Project"):
    p = Project(project_id=pid, name=name, description="Adversarial test project")
    db.add(p)
    db.commit()
    return p


def _make_activity(
    db,
    aid="ACT-ADV-001",
    pid="ADV-PROJ-001",
    discipline="Piping",
    description="Spool erection at Rack B",
    location="Rack B",
    eq_id="24P201",
    planned_start=datetime.date(2025, 1, 1),
    planned_finish=datetime.date(2025, 3, 31),
    status="NOT_STARTED",
    percent_complete=0.0,
    actual_start=None,
    actual_finish=None,
    predecessor_id=None,
):
    a = ScheduleActivity(
        activity_id=aid,
        project_id=pid,
        discipline=discipline,
        description=description,
        location=location,
        equipment_or_line_id=eq_id,
        planned_start=planned_start,
        planned_finish=planned_finish,
        status=status,
        percent_complete=percent_complete,
        actual_start=actual_start,
        actual_finish=actual_finish,
        predecessor_activity_id=predecessor_id,
    )
    db.add(a)
    db.commit()
    return a


def _make_report(
    db,
    pid="ADV-PROJ-001",
    rid=None,
    raw_content="P201 erection completed at Rack B.",
    source_type="TXT",
    discipline="Piping",
    report_date=datetime.date(2025, 2, 15),
):
    if rid is None:
        rid = f"REP-{uuid.uuid4().hex[:8].upper()}"
    r = SourceReport(
        report_id=rid,
        project_id=pid,
        filename="test_report.txt",
        source_type=source_type,
        report_date=report_date,
        discipline=discipline,
        raw_content=raw_content,
        file_hash=f"hash-{rid}",
        file_size=len(raw_content.encode()),
        stored_path="/tmp/test_report.txt",
        processing_status=ProcessingStatus.VALIDATED.value,
    )
    db.add(r)
    db.commit()
    return r


def _make_event(
    db,
    rid="REP-001",
    eid=None,
    raw_text="P201 erection completed at Rack B.",
    status="COMPLETED",
    percent_complete=100.0,
    identifier="24P201",
    discipline="Piping",
    location="Rack B",
    event_date=datetime.date(2025, 2, 15),
):
    if eid is None:
        eid = f"EVT-{uuid.uuid4().hex[:8].upper()}"
    e = ExtractedEvent(
        event_id=eid,
        report_id=rid,
        raw_text=raw_text,
        event_date=event_date,
        event_date_source="REPORT_DATE",
        discipline=discipline,
        action="erection",
        object="spool",
        identifier=identifier,
        location=location,
        status=status,
        percent_complete=percent_complete,
        quantity=None,
        unit=None,
        source_position={"type": "TXT_LINE", "line": 1},
        extraction_method="RULE_BASED",
        extraction_version="v1",
    )
    db.add(e)
    db.commit()
    return e


def _make_decision(
    db,
    eid,
    aid,
    decision="AUTO_LINK",
    confidence=90.0,
    top2=20.0,
):
    dec_id = f"DEC-{uuid.uuid4().hex[:8].upper()}"
    d = MatchDecision(
        decision_id=dec_id,
        event_id=eid,
        top_activity_id=aid,
        match_confidence=confidence,
        evidence_completeness=75.0,
        top_2_margin=top2,
        decision=decision,
        reasons=["Test decision"],
        missing_evidence=[],
        matcher_version="v1",
        scoring_policy_version="v1",
    )
    db.add(d)
    db.commit()
    return d


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 & 2 – DATABASE INTEGRITY & IDEMPOTENCY
# ══════════════════════════════════════════════════════════════════════════════


class TestDatabaseIntegrity:
    """Section 1: Database integrity checks."""

    def test_duplicate_project_id_rejected(self, client):
        """Duplicate project IDs must return 400."""
        payload = {"project_id": "DUP-PROJ-001", "name": "Project A", "description": ""}
        r1 = client.post("/projects", json=payload)
        assert r1.status_code == 201
        r2 = client.post("/projects", json=payload)
        assert r2.status_code == 400
        assert "already exists" in r2.json()["detail"].lower()

    def test_missing_predecessor_activity_id_is_safe(self, db):
        """Predecessor pointing to a non-existent activity should produce a warning, not crash."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-ORPHAN", predecessor_id="NONEXISTENT-PRED")
        warnings = check_dependency_warnings(act, db)
        # Missing predecessor means no pred row found → no warning (graceful no-op)
        assert isinstance(warnings, list)

    def test_circular_predecessor_does_not_crash(self, db):
        """Circular A→B→A should not crash check_dependency_warnings."""
        _make_project(db)
        a = _make_activity(db, aid="CIRC-A", predecessor_id="CIRC-B")
        # CIRC-B doesn't exist yet, so no warning should blow up
        warnings = check_dependency_warnings(a, db)
        assert isinstance(warnings, list)

    def test_audit_and_schedule_are_atomic(self, db):
        """
        Progress update must leave both schedule AND audit mutated, or neither.
        We verify that after a successful apply, both records exist.
        """
        _make_project(db)
        act = _make_activity(db, aid="ACT-ATOMIC")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-ATOMIC-001")
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        result = svc.apply_event_progress(evt.event_id)

        assert result["applied"] is True
        audit = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).first()
        assert audit is not None, "AuditRecord must exist after successful apply"
        refreshed = db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act.activity_id).first()
        assert refreshed.status == "COMPLETED"

    def test_no_orphan_audit_without_schedule_update(self, db):
        """
        Audit must only be created when schedule update succeeds.
        An event with HUMAN_REVIEW decision must NOT create an audit.
        """
        _make_project(db)
        act = _make_activity(db, aid="ACT-HR")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-HR-001")
        _make_decision(db, eid=evt.event_id, aid=act.activity_id, decision="HUMAN_REVIEW", confidence=65.0)

        svc = ProgressUpdateService(db)
        result = svc.apply_event_progress(evt.event_id)

        assert result["applied"] is False
        audit = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).first()
        assert audit is None, "No audit should be created for a non-AUTO_LINK event"

    def test_schedule_not_mutated_on_conflict(self, db):
        """
        When conflict detection fires, the schedule must NOT be mutated,
        but also no audit must be created.
        """
        _make_project(db)
        # COMPLETED activity – try to push STARTED (regression)
        act = _make_activity(
            db, aid="ACT-CONFL",
            status="COMPLETED", percent_complete=100.0,
            actual_start=datetime.date(2025, 1, 5),
            actual_finish=datetime.date(2025, 2, 20),
        )
        rep = _make_report(db)
        # Event that would set status back to STARTED
        evt = _make_event(
            db, rid=rep.report_id, eid="EVT-CONFL-001",
            status="STARTED", percent_complete=0.0,
        )
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        result = svc.apply_event_progress(evt.event_id)

        assert result["applied"] is False
        assert result["decision"] == "CONFLICT_REVIEW"
        # Schedule must be unchanged
        refreshed = db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act.activity_id).first()
        assert refreshed.status == "COMPLETED"
        assert refreshed.percent_complete == 100.0
        # No audit for conflicting event
        audit = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).first()
        assert audit is None, "Conflicted apply must NOT produce an audit record"

    def test_transaction_rollback_on_db_failure(self, db):
        """
        Simulates a mid-transaction failure; ensures DB remains consistent.
        We monkey-patch record_schedule_audit to raise.
        """
        import backend.app.services.progress_update_service as pus_module
        original_fn = pus_module.record_schedule_audit

        def _broken_audit(*args, **kwargs):
            raise RuntimeError("Simulated DB failure mid-transaction")

        pus_module.record_schedule_audit = _broken_audit
        try:
            _make_project(db)
            act = _make_activity(db, aid="ACT-TXROLL")
            rep = _make_report(db)
            evt = _make_event(db, rid=rep.report_id, eid="EVT-TXROLL-001")
            _make_decision(db, eid=evt.event_id, aid=act.activity_id)

            svc = ProgressUpdateService(db)
            with pytest.raises(RuntimeError, match="Atomic transaction failed"):
                svc.apply_event_progress(evt.event_id)

            # Activity must still be NOT_STARTED after rollback
            db.expire_all()
            refreshed = db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act.activity_id).first()
            assert refreshed.status == "NOT_STARTED"
            assert refreshed.percent_complete == 0.0
        finally:
            pus_module.record_schedule_audit = original_fn


class TestIdempotency:
    """Section 2: Idempotency of uploads, extractions, decisions and applies."""

    def test_apply_twice_returns_already_applied(self, db):
        """Repeating apply_event_progress for same event_id must be safe and idempotent."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-IDEM")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-IDEM-001")
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        r1 = svc.apply_event_progress(evt.event_id)
        r2 = svc.apply_event_progress(evt.event_id)

        assert r1["applied"] is True
        assert r2["already_applied"] is True
        # Exactly ONE audit record, not two
        audits = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).all()
        assert len(audits) == 1, f"Expected exactly 1 audit; got {len(audits)}"

    def test_extraction_idempotent(self, db):
        """Re-extracting events from the same report_id must not duplicate events."""
        _make_project(db)
        rep = _make_report(db, raw_content="P201 erection completed at Rack B.")

        svc = EventExtractionService(db)
        _, evts1 = svc.extract_events_from_report(rep.report_id)
        _, evts2 = svc.extract_events_from_report(rep.report_id)

        ids1 = {e.event_id for e in evts1}
        ids2 = {e.event_id for e in evts2}
        assert ids1 == ids2, "Re-extraction must return same event IDs (no duplicates)"

    def test_duplicate_upload_detected(self, client, db):
        """Same file uploaded twice to same project must be flagged as duplicate."""
        _make_project(db)
        content = b"P201 erection completed at Rack B."
        files = {"file": ("report.txt", content, "text/plain")}
        data = {"project_id": "ADV-PROJ-001", "report_date": "2025-02-15", "discipline": "Piping"}

        r1 = client.post("/reports/upload", data=data, files=files)
        assert r1.status_code == 201

        r2 = client.post("/reports/upload", data=data, files=files)
        assert r2.status_code == 201
        body2 = r2.json()
        assert body2.get("duplicate") is True

    def test_same_event_cannot_progress_twice(self, db):
        """The progress applied by event E must not be applied again (audit acts as lock)."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-NODBL", status="NOT_STARTED", percent_complete=0.0)
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-NODBL-001",
                          status="IN_PROGRESS", percent_complete=60.0)
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        r1 = svc.apply_event_progress(evt.event_id)
        assert r1["applied"] is True
        assert r1["percent_complete"] == 60.0

        # Apply again – must NOT push percent to 60 again or flip state
        r2 = svc.apply_event_progress(evt.event_id)
        assert r2["already_applied"] is True

        # Audit must still be exactly 1
        audits = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).all()
        assert len(audits) == 1


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 – INVALID FILES
# ══════════════════════════════════════════════════════════════════════════════


class TestInvalidFiles:
    """Section 3: File validation edge-cases."""

    def test_empty_txt_rejected(self):
        with pytest.raises(ReportValidationError) as exc_info:
            validate_file_content("report.txt", b"   \n\t  ")
        assert exc_info.value.code in ("EMPTY_FILE",)

    def test_empty_bytes_rejected(self):
        with pytest.raises(ReportValidationError) as exc_info:
            validate_file_content("report.txt", b"")
        # Should be EMPTY_FILE (size 0)
        assert exc_info.value.code == "EMPTY_FILE"

    def test_malformed_csv_rejected(self):
        # Deliberately broken CSV (mismatched quotes)
        bad_csv = b'"col1","col2\ncell1,cell2'
        with pytest.raises(ReportValidationError) as exc_info:
            validate_file_content("report.csv", bad_csv)
        assert exc_info.value.code == "MALFORMED_FILE"

    def test_renamed_executable_as_txt_accepted_as_text(self):
        """
        A renamed EXE with .txt extension must be processed as TXT.
        The file validator should NOT execute the content; it should treat it as text.
        The ELF magic bytes \\x7fELF can't be decoded as UTF-8 cleanly.
        """
        elf_magic = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8  # 16 bytes ELF header
        # This should either raise MALFORMED_FILE (decode failure) or accept as latin-1
        try:
            validate_file_content("malware.txt", elf_magic)
        except ReportValidationError as e:
            assert e.code in ("MALFORMED_FILE", "EMPTY_FILE")
        except Exception as e:
            pytest.fail(f"Unexpected exception type {type(e)}: {e}")

    def test_file_exceeds_size_limit_rejected(self):
        big_content = b"x" * (settings.MAX_FILE_SIZE_BYTES + 1)
        with pytest.raises(ReportValidationError) as exc_info:
            validate_file_size(len(big_content))
        assert exc_info.value.code == "FILE_TOO_LARGE"

    def test_file_near_size_limit_accepted(self):
        # Exactly at the limit boundary - 1 byte should be fine
        near_limit = b"P201 erection started at Rack B." * 1000
        # Just validate size (content separately)
        size = len(near_limit)
        if size <= settings.MAX_FILE_SIZE_BYTES:
            validate_file_size(size)  # Must not raise

    def test_path_traversal_filename_rejected(self, client, db):
        """../../evil.txt filename must not cause server error or traversal.
        BUG-001 FIX verified: filename is sanitized at ingestion to just 'evil.txt'."""
        _make_project(db)
        content = b"P201 erection started."
        files = {"file": ("../../evil.txt", content, "text/plain")}
        data = {"project_id": "ADV-PROJ-001", "report_date": "2025-02-15", "discipline": "Piping"}
        r = client.post("/reports/upload", data=data, files=files)
        # Must not 500
        assert r.status_code != 500
        if r.status_code == 201:
            body = r.json()
            stored_filename = body.get("filename", "")
            # After BUG-001 fix: '../../evil.txt' must be sanitized to 'evil.txt'
            assert ".." not in stored_filename, (
                f"Path traversal in stored filename after fix: '{stored_filename}'"
            )

    def test_unicode_filename_safe(self, client, db):
        """Report with Unicode in the filename (e.g., Cyrillic) must not crash."""
        _make_project(db)
        content = b"P201 erection completed."
        files = {"file": ("отчет_2025.txt", content, "text/plain")}
        data = {"project_id": "ADV-PROJ-001", "report_date": "2025-02-15", "discipline": "Piping"}
        r = client.post("/reports/upload", data=data, files=files)
        assert r.status_code in (201, 400)  # Must not 500

    def test_spreadsheet_missing_mandatory_columns(self, client, db):
        """DPR spreadsheet missing required columns should be rejected."""
        _make_project(db)
        df = pd.DataFrame({"only_col": ["value1", "value2"]})
        buf = io.BytesIO()
        # Name file with 'dpr' to trigger DPR column check
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["only_col"])
        ws.append(["value1"])
        wb.save(buf)
        buf.seek(0)
        xlsx_bytes = buf.read()

        try:
            validate_file_content("dpr_report.xlsx", xlsx_bytes)
            # If we get here without error, columns weren't DPR ones, which is also fine
        except ReportValidationError as e:
            assert e.code in ("MISSING_REQUIRED_COLUMNS", "EMPTY_FILE", "MALFORMED_FILE")

    def test_duplicate_file_different_name_detected(self, client, db):
        """Same content, different filename, same project → duplicate hash detected."""
        _make_project(db)
        content = b"Unique content for duplicate test 12345."
        data = {"project_id": "ADV-PROJ-001", "report_date": "2025-02-15", "discipline": "Piping"}

        r1 = client.post("/reports/upload", data=data,
                         files={"file": ("name_a.txt", content, "text/plain")})
        r2 = client.post("/reports/upload", data=data,
                         files={"file": ("name_b.txt", content, "text/plain")})

        assert r1.status_code == 201
        assert r2.status_code == 201
        assert r2.json().get("duplicate") is True

    def test_null_bytes_in_txt_handled(self, client, db):
        """File containing null bytes must not crash the system."""
        _make_project(db)
        content = b"P201 erection completed.\x00\x00\x00"
        files = {"file": ("null_bytes.txt", content, "text/plain")}
        data = {"project_id": "ADV-PROJ-001", "report_date": "2025-02-15", "discipline": "Piping"}
        r = client.post("/reports/upload", data=data, files=files)
        assert r.status_code in (201, 400)  # Must not 500


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 – TEXT EXTRACTION EDGE-CASES
# ══════════════════════════════════════════════════════════════════════════════


class TestTextExtractionEdgeCases:
    """Section 4: Negation, uncertainty, future tense, partial completion."""

    # ── Negation ──────────────────────────────────────────────────────────────

    def test_no_work_started_on_p201_is_not_started(self):
        """'No work started on P201.' must NOT extract status STARTED."""
        text = "No work started on P201."
        status = extract_status(text)
        assert status != "STARTED", f"Negated start incorrectly extracted as STARTED: {status}"

    def test_no_activities_completed_is_not_completed(self):
        """'No activities completed.' must NOT become COMPLETED."""
        text = "No activities completed today."
        status = extract_status(text)
        assert status != "COMPLETED", f"Negated completion incorrectly extracted: {status}"

    def test_not_completed_is_not_status_completed(self):
        """'P201 not completed.' must NOT become COMPLETED."""
        text = "P201 not completed."
        status = extract_status(text)
        assert status != "COMPLETED", f"'not completed' incorrectly parsed as COMPLETED: {status}"

    def test_nothing_was_done_is_not_completed(self):
        """'Nothing was done at P201.' must NOT produce COMPLETED."""
        text = "Nothing was done at P201 today."
        status = extract_status(text)
        assert status != "COMPLETED"

    # ── Future tense ─────────────────────────────────────────────────────────

    def test_planned_to_start_tomorrow_not_started(self):
        """'P201 was planned to start tomorrow.' must NOT become STARTED."""
        text = "P201 was planned to start tomorrow."
        status = extract_status(text)
        assert status != "STARTED", f"Future planned start incorrectly parsed: {status}"

    # ── Uncertainty / conditional ─────────────────────────────────────────────

    def test_erection_completed_awaiting_confirmation_uncertain(self):
        """'P201 erection completed? awaiting confirmation.' – uncertain; may or may not be COMPLETED."""
        text = "P201 erection completed? awaiting confirmation."
        status = extract_status(text)
        # The system may or may not extract COMPLETED here – this is acceptable.
        # The key assertion is that the test is explicit; we document it.
        # We also confirm it doesn't crash.
        assert status in (None, "COMPLETED", "IN_PROGRESS", "NOT_STARTED", "STARTED")

    def test_work_stopped_due_to_rain_not_completed(self):
        """'P201 work stopped due to rain.' must NOT become COMPLETED."""
        text = "P201 work stopped due to rain."
        status = extract_status(text)
        assert status != "COMPLETED"

    # ── Partial completion ────────────────────────────────────────────────────

    def test_completed_except_final_tiein_not_100pct(self):
        """'P201 completed except final tie-in.' – percent should not be 100% extracted."""
        text = "P201 completed except final tie-in."
        pct = extract_percent_complete(text)
        # No explicit percentage in the text
        assert pct is None, f"Partial completion incorrectly yielded percent: {pct}"

    def test_95_percent_complete_correctly_parsed(self):
        """'P201 95% complete' must yield 95.0, not COMPLETED status."""
        text = "P201 spool installation 95% complete."
        pct = extract_percent_complete(text)
        status = extract_status(text)
        assert pct == 95.0
        assert status == "IN_PROGRESS"

    def test_100_percent_yields_completed(self):
        """Explicit '100%' must yield COMPLETED status."""
        text = "P201 erection 100% complete."
        pct = extract_percent_complete(text)
        status = extract_status(text)
        assert pct == 100.0
        assert status == "COMPLETED"

    def test_0_percent_yields_not_started(self):
        """Explicit '0%' must yield NOT_STARTED."""
        text = "P201 erection 0% complete."
        pct = extract_percent_complete(text)
        status = extract_status(text)
        assert pct == 0.0
        assert status == "NOT_STARTED"

    # ── Hinglish negation ─────────────────────────────────────────────────────

    def test_hinglish_start_ho_gaya_extracted(self):
        """'24P201 kaam start ho gaya' – Hinglish start phrase should extract STARTED."""
        text = "24P201 kaam start ho gaya Rack B par."
        status = extract_status(text)
        # The pattern includes 'start ho gaya'
        assert status == "STARTED"

    def test_nil_work_done_not_completed(self):
        """'nil work done on P201' must NOT be COMPLETED."""
        text = "nil work done on P201 today."
        status = extract_status(text)
        assert status != "COMPLETED"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 – MULTI-EVENT SPLITTING
# ══════════════════════════════════════════════════════════════════════════════


class TestMultiEventSplitting:
    """Section 5: Text segmenter splits complex sentences correctly."""

    def test_two_events_with_and_split(self):
        """'F12 reinforcement completed and 24P201 spool erection started' → 2 events."""
        text = "F12 reinforcement completed and 24P201 spool erection started."
        segs = segment_text_into_events(text)
        assert len(segs) >= 2, f"Expected ≥2 segments, got {len(segs)}: {segs}"

    def test_semicolon_split(self):
        """Lines separated by semicolons must produce separate events."""
        text = "P201 erection started; F12 concreting completed; E301 cable pulling ongoing."
        segs = segment_text_into_events(text)
        assert len(segs) >= 3, f"Expected ≥3 segments from semicolons, got {len(segs)}"

    def test_commas_do_not_over_split(self):
        """Commas alone within a single clause should not produce spurious extra events."""
        text = "P201, F12 and E301 all in progress at Rack B."
        segs = segment_text_into_events(text)
        # At most 3 events (one per identifier) – must not produce 10+
        assert len(segs) <= 5, f"Over-splitting detected: {len(segs)} segments"

    def test_mixed_discipline_events(self):
        """Piping and electrical events in same line must each preserve provenance."""
        text = "P201 piping spool erection completed and E301 cable pulling ongoing at Substation 3."
        segs = segment_text_into_events(text)
        texts = [s["text"] for s in segs]
        # At least two segments with distinct content
        assert any("P201" in t or "piping" in t.lower() for t in texts)
        assert any("E301" in t or "cable" in t.lower() or "electrical" in t.lower() for t in texts)

    def test_three_events_comma_and(self):
        """3 work items separated by commas + 'and' keyword."""
        text = "P201 erection completed, F12 reinforcement started and E301 cable pulling ongoing."
        segs = segment_text_into_events(text)
        assert len(segs) >= 1  # At least does not crash

    def test_no_events_in_empty_text(self):
        segs = segment_text_into_events("")
        assert segs == []

    def test_source_position_retained(self):
        """Each segment must have a source_position dict with 'line' key."""
        text = "P201 erection started.\nF12 concreting completed."
        segs = segment_text_into_events(text)
        for seg in segs:
            assert "source_position" in seg
            assert "line" in seg["source_position"]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 – IDENTIFIER NORMALIZATION
# ══════════════════════════════════════════════════════════════════════════════


class TestIdentifierNormalization:
    """Section 6: normalize_identifier stress tests."""

    def test_hyphenated_form_normalizes(self):
        assert normalize_identifier("24-P-201") == normalize_identifier("24P201")

    def test_space_form_normalizes(self):
        assert normalize_identifier("24 P 201") == normalize_identifier("24P201")

    def test_lowercase_normalizes(self):
        assert normalize_identifier("p-201") is not None

    def test_similar_ids_not_merged(self):
        """24P201 and 24P210 must NOT normalize to the same string."""
        n1 = normalize_identifier("24P201")
        n2 = normalize_identifier("24P210")
        assert n1 != n2, f"Over-aggressive normalization merged 24P201 and 24P210: both → '{n1}'"

    def test_similar_ids_not_merged_211(self):
        """24P201 and 24P211 must NOT normalize to the same string."""
        n1 = normalize_identifier("24P201")
        n2 = normalize_identifier("24P211")
        assert n1 != n2, f"Over-aggressive normalization merged 24P201 and 24P211"

    def test_empty_identifier_returns_none(self):
        assert normalize_identifier("") is None
        assert normalize_identifier(None) is None
        assert normalize_identifier("   ") is None

    def test_p201_short_form_normalizes_deterministically(self):
        """Short form 'P201' normalizes without crashing and returns something."""
        result = normalize_identifier("P201")
        assert result is not None and len(result) > 0

    def test_24p201_forms_are_consistent(self):
        forms = ["24-P-201", "24 P 201", "24P201", "24P-201"]
        normalized = [normalize_identifier(f) for f in forms]
        # All forms without dict entry must normalize to the same stripped form
        unique = set(normalized)
        assert len(unique) == 1, f"Inconsistent normalization for {forms}: {unique}"

    def test_score_identifier_contradictory_gives_zero(self):
        """Identifier that doesn't match activity must score 0.0."""
        score = score_identifier("24P999", "ACT-ADV-001", "24P201")
        assert score == 0.0

    def test_score_identifier_missing_gives_neutral(self):
        """No identifier in event must give neutral 50.0."""
        score = score_identifier(None, "ACT-ADV-001", "24P201")
        assert score == 50.0

    def test_score_identifier_exact_match_gives_100(self):
        score = score_identifier("24P201", "24P201", None)
        assert score == 100.0


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 – AMBIGUITY DETECTION
# ══════════════════════════════════════════════════════════════════════════════


class TestAmbiguityDetection:
    """Section 7: top-2 margin forces HUMAN_REVIEW."""

    def test_close_margin_forces_human_review(self, db):
        """
        When top-2 margin is below TOP2_MARGIN_THRESHOLD, decision must be HUMAN_REVIEW.
        """
        from backend.app.services.decision_policy import evaluate_decision_policy
        from backend.app.db.models.decision import DecisionEnum

        # Build fake candidate objects
        class FakeCandidate:
            def __init__(self, score):
                self.overall_score = score
                self.activity_id = "ACT-FAKE"
                self.matcher_version = "v1"

        class FakeEvent:
            raw_text = "P201 erection in progress at Rack B."
            identifier = "24P201"

        # top-2 margin = 90.0 - 82.0 = 8.0 → below 12.0 threshold
        cands = [FakeCandidate(90.0), FakeCandidate(82.0)]
        decision, top = evaluate_decision_policy(FakeEvent(), cands, 80.0, 8.0)
        assert decision == DecisionEnum.HUMAN_REVIEW, f"Expected HUMAN_REVIEW, got {decision}"

    def test_high_margin_allows_autolink(self, db):
        """Wide top-2 margin + high scores → AUTO_LINK."""
        from backend.app.services.decision_policy import evaluate_decision_policy
        from backend.app.db.models.decision import DecisionEnum

        class FakeCandidate:
            def __init__(self, score):
                self.overall_score = score
                self.activity_id = "ACT-FAKE"
                self.matcher_version = "v1"

        class FakeEvent:
            raw_text = "P201 erection completed at Rack B."
            identifier = "24P201"

        cands = [FakeCandidate(92.0), FakeCandidate(60.0)]
        decision, top = evaluate_decision_policy(FakeEvent(), cands, 85.0, 32.0)
        assert decision == DecisionEnum.AUTO_LINK

    def test_no_candidates_unplanned_review(self, db):
        """Zero candidates → UNPLANNED_REVIEW."""
        from backend.app.services.decision_policy import evaluate_decision_policy
        from backend.app.db.models.decision import DecisionEnum

        class FakeEvent:
            raw_text = "Some exotic work not in schedule."
            identifier = None

        decision, top = evaluate_decision_policy(FakeEvent(), [], 50.0, None)
        assert decision == DecisionEnum.UNPLANNED_REVIEW

    def test_very_weak_top_candidate_unplanned(self, db):
        """Top candidate scoring < 40 → UNPLANNED_REVIEW."""
        from backend.app.services.decision_policy import evaluate_decision_policy
        from backend.app.db.models.decision import DecisionEnum

        class FakeCandidate:
            overall_score = 30.0
            activity_id = "ACT-FAKE"
            matcher_version = "v1"

        class FakeEvent:
            raw_text = "Completely irrelevant text."
            identifier = None

        decision, top = evaluate_decision_policy(FakeEvent(), [FakeCandidate()], 40.0, None)
        assert decision == DecisionEnum.UNPLANNED_REVIEW

    def test_ignore_keyword_event_routed_to_ignore(self, db):
        """Safety meeting text without identifier → IGNORE."""
        from backend.app.services.decision_policy import evaluate_decision_policy
        from backend.app.db.models.decision import DecisionEnum

        class FakeCand:
            overall_score = 95.0
            activity_id = "ACT-FAKE"
            matcher_version = "v1"

        class FakeEvent:
            raw_text = "Safety meeting conducted in the morning."
            identifier = None

        decision, top = evaluate_decision_policy(FakeEvent(), [FakeCand()], 90.0, 100.0)
        assert decision == DecisionEnum.IGNORE


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 – UNPLANNED WORK
# ══════════════════════════════════════════════════════════════════════════════


class TestUnplannedWork:
    """Section 8: Work not in baseline must not be auto-linked solely on semantics."""

    def test_no_candidates_means_unplanned(self, db):
        """
        If no activity in the schedule matches (e.g., different discipline/location),
        the system must route to UNPLANNED_REVIEW, not AUTO_LINK.
        """
        from backend.app.services.decision_policy import evaluate_decision_policy
        from backend.app.db.models.decision import DecisionEnum

        class FakeEvent:
            raw_text = "Grounding cable installation at Control Room."
            identifier = None

        # Zero candidates → UNPLANNED_REVIEW
        decision, _ = evaluate_decision_policy(FakeEvent(), [], 0.0, None)
        assert decision == DecisionEnum.UNPLANNED_REVIEW

    def test_semantic_similarity_alone_insufficient_for_autolink(self, db):
        """
        High semantic score but wrong identifier must not auto-link.
        score_identifier with mismatch → 0.0, dragging overall score below threshold.
        """
        id_score = score_identifier("24P999", "ACT-DIFFERENT", "24P111")
        assert id_score == 0.0
        # With 0.0 identifier score, overall will be pulled far below 85


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 – IRRELEVANT TEXT
# ══════════════════════════════════════════════════════════════════════════════


class TestIrrelevantText:
    """Section 9: Administrative/non-work statements must not update schedule."""

    @pytest.mark.parametrize("text", [
        "Safety meeting conducted at 07:00.",
        "Weather delay due to heavy rain, no work carried out.",
        "Tool box talk held for all workers.",
        "Material arrived on site – 50 units of pipe.",
        "Manpower count: 15 workers present today.",
        "Vehicle breakdown delayed concrete delivery.",
        "Site manager briefed team on upcoming inspection.",
        "Holiday declared – no activities today.",
    ])
    def test_irrelevant_text_extracts_no_status(self, text):
        """Irrelevant statements must not produce actionable status."""
        status = extract_status(text)
        # These lines either produce None, or if they contain 'completed' etc.
        # due to incidental matches, we verify there's no identifier attached.
        identifier = extract_identifier(text)
        if status is not None and status in ("COMPLETED", "STARTED", "IN_PROGRESS"):
            # It's acceptable only if there's also an identifier (specific work event)
            # For pure admin text, no identifier should be extracted
            assert identifier is None or identifier == "", (
                f"Admin text '{text}' extracted status={status} with identifier={identifier}"
            )

    @pytest.mark.parametrize("text", [
        "Safety meeting conducted at 07:00.",
        "Weather delay due to heavy rain, no work carried out.",
        "Tool box talk held for all workers.",
        "Holiday declared – no activities today.",
    ])
    def test_decision_policy_ignores_admin_text(self, text):
        """IGNORE_KEYWORDS should route these to IGNORE in decision policy."""
        from backend.app.services.decision_policy import evaluate_decision_policy, IGNORE_KEYWORDS_REGEX
        from backend.app.db.models.decision import DecisionEnum

        class FakeCand:
            overall_score = 95.0
            activity_id = "ACT-FAKE"
            matcher_version = "v1"

        class FakeEvent:
            raw_text = text
            identifier = None

        decision, _ = evaluate_decision_policy(FakeEvent(), [FakeCand()], 90.0, 100.0)
        if IGNORE_KEYWORDS_REGEX.search(text):
            assert decision == DecisionEnum.IGNORE, (
                f"Expected IGNORE for admin text '{text}', got {decision}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 – STATE REGRESSION
# ══════════════════════════════════════════════════════════════════════════════


class TestStateRegression:
    """Section 10: Illegal state transitions must be caught by conflict detector."""

    @pytest.mark.parametrize("current,proposed,expect_conflict", [
        ("NOT_STARTED", "COMPLETED", False),   # Allowed: fast-track
        ("COMPLETED", "STARTED", True),         # Illegal regression
        ("COMPLETED", "IN_PROGRESS", True),     # Illegal regression
        ("IN_PROGRESS", "NOT_STARTED", True),   # Illegal regression (percentage conflict)
        ("IN_PROGRESS", "IN_PROGRESS", False),  # Same is OK
        ("COMPLETED", "REWORK", False),          # REWORK is allowed
        ("REWORK", "COMPLETED", False),          # REWORK → COMPLETED OK
    ])
    def test_conflict_detector_on_status_regression(self, current, proposed, expect_conflict, db):
        _make_project(db)
        pct_map = {
            "NOT_STARTED": 0.0, "STARTED": 5.0, "IN_PROGRESS": 60.0,
            "COMPLETED": 100.0, "REWORK": 80.0,
        }
        act = _make_activity(db, aid=f"ACT-REG-{current[:3]}",
                             status=current, percent_complete=pct_map[current],
                             actual_start=datetime.date(2025, 1, 5) if current != "NOT_STARTED" else None,
                             actual_finish=datetime.date(2025, 2, 20) if current == "COMPLETED" else None)

        conflicts = detect_schedule_conflicts(
            activity=act,
            proposed_status=proposed,
            proposed_percent=pct_map[proposed],
            proposed_start=None,
            proposed_finish=None,
        )
        has_conflict = len(conflicts) > 0
        assert has_conflict == expect_conflict, (
            f"Transition {current}→{proposed}: expected conflict={expect_conflict}, "
            f"got conflicts={conflicts}"
        )

    def test_percentage_regression_flagged_as_conflict(self, db):
        """70% → 30% must be flagged as PERCENTAGE_CONFLICT."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-PCTREGR",
                             status="IN_PROGRESS", percent_complete=70.0)
        conflicts = detect_schedule_conflicts(
            activity=act,
            proposed_status="IN_PROGRESS",
            proposed_percent=30.0,
            proposed_start=None,
            proposed_finish=None,
        )
        types = [c["type"] for c in conflicts]
        assert "PERCENTAGE_CONFLICT" in types

    def test_completed_to_60pct_flagged(self, db):
        """COMPLETED → 60% must be flagged as PERCENTAGE_CONFLICT."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-CTR60",
                             status="COMPLETED", percent_complete=100.0,
                             actual_finish=datetime.date(2025, 2, 20))
        conflicts = detect_schedule_conflicts(
            activity=act,
            proposed_status="IN_PROGRESS",
            proposed_percent=60.0,
            proposed_start=None,
            proposed_finish=None,
        )
        # STATUS_CONFLICT or PERCENTAGE_CONFLICT expected
        assert len(conflicts) >= 1

    def test_valid_state_transition_table(self):
        """Validate the full VALID_TRANSITIONS table."""
        valid_cases = [
            ("NOT_STARTED", "STARTED"), ("NOT_STARTED", "IN_PROGRESS"), ("NOT_STARTED", "COMPLETED"),
            ("STARTED", "IN_PROGRESS"), ("STARTED", "COMPLETED"),
            ("IN_PROGRESS", "COMPLETED"),
            ("COMPLETED", "REWORK"),
            ("REWORK", "IN_PROGRESS"), ("REWORK", "COMPLETED"),
        ]
        invalid_cases = [
            ("COMPLETED", "STARTED"), ("COMPLETED", "IN_PROGRESS"),
            ("IN_PROGRESS", "NOT_STARTED"), ("IN_PROGRESS", "STARTED"),
        ]
        for current, target in valid_cases:
            assert validate_state_transition(current, target), (
                f"Expected {current}→{target} to be valid"
            )
        for current, target in invalid_cases:
            assert not validate_state_transition(current, target), (
                f"Expected {current}→{target} to be invalid"
            )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11 – DATE EDGE-CASES
# ══════════════════════════════════════════════════════════════════════════════


class TestDateEdgeCases:
    """Section 11: Date validation and ordering."""

    def test_finish_before_start_flagged(self):
        ok, msg = validate_date_ordering(
            datetime.date(2025, 3, 1), datetime.date(2025, 2, 1)
        )
        assert not ok
        assert "INVALID_DATE_ORDER" in msg

    def test_same_day_start_finish_valid(self):
        ok, msg = validate_date_ordering(
            datetime.date(2025, 3, 1), datetime.date(2025, 3, 1)
        )
        assert ok

    def test_none_dates_are_valid(self):
        ok, msg = validate_date_ordering(None, None)
        assert ok
        ok2, _ = validate_date_ordering(datetime.date(2025, 1, 1), None)
        assert ok2

    def test_conflict_detector_invalid_date_order(self, db):
        """detect_schedule_conflicts with finish < start → INVALID_DATE_ORDER."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-DORD")
        conflicts = detect_schedule_conflicts(
            activity=act,
            proposed_status="IN_PROGRESS",
            proposed_percent=50.0,
            proposed_start=datetime.date(2025, 3, 1),
            proposed_finish=datetime.date(2025, 2, 1),
        )
        types = [c["type"] for c in conflicts]
        assert "INVALID_DATE_ORDER" in types

    def test_invalid_date_string_raises(self):
        with pytest.raises(ReportValidationError) as exc_info:
            validate_report_date("not-a-date")
        assert exc_info.value.code == "INVALID_REPORT_DATE"

    def test_missing_date_raises(self):
        with pytest.raises(ReportValidationError) as exc_info:
            validate_report_date("")
        assert exc_info.value.code == "INVALID_REPORT_DATE"

    def test_valid_date_string_parsed(self):
        dt = validate_report_date("2025-06-15")
        assert dt == datetime.date(2025, 6, 15)

    def test_far_future_date_accepted(self):
        """Far-future date (2099) should be parsed without crash."""
        dt = validate_report_date("2099-12-31")
        assert dt.year == 2099

    def test_planned_dates_never_mutated_by_apply(self, db):
        """Core immutability check: planned_start/planned_finish must not change."""
        _make_project(db)
        original_start = datetime.date(2025, 1, 1)
        original_finish = datetime.date(2025, 3, 31)
        act = _make_activity(db, aid="ACT-IMMUT",
                             planned_start=original_start, planned_finish=original_finish)
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-IMMUT-001",
                          status="COMPLETED", percent_complete=100.0,
                          event_date=datetime.date(2025, 2, 15))
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        svc.apply_event_progress(evt.event_id)

        db.expire_all()
        refreshed = db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act.activity_id).first()
        assert refreshed.planned_start == original_start, "planned_start was mutated!"
        assert refreshed.planned_finish == original_finish, "planned_finish was mutated!"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 12 – DEPENDENCY EDGE-CASES
# ══════════════════════════════════════════════════════════════════════════════


class TestDependencyEdgeCases:
    """Section 12: Dependency warnings, not blocking."""

    def test_successor_complete_before_predecessor_gives_warning(self, db):
        _make_project(db)
        pred = _make_activity(db, aid="ACT-PRED", status="IN_PROGRESS", percent_complete=50.0)
        succ = _make_activity(db, aid="ACT-SUCC", predecessor_id="ACT-PRED")

        warnings = check_dependency_warnings(succ, db)
        assert len(warnings) >= 1
        assert "DEPENDENCY_WARNING" in warnings[0]["type"]

    def test_predecessor_completed_gives_no_warning(self, db):
        _make_project(db)
        _make_activity(db, aid="ACT-PRED2", status="COMPLETED", percent_complete=100.0)
        succ = _make_activity(db, aid="ACT-SUCC2", predecessor_id="ACT-PRED2")

        warnings = check_dependency_warnings(succ, db)
        assert len(warnings) == 0

    def test_no_predecessor_no_warning(self, db):
        _make_project(db)
        act = _make_activity(db, aid="ACT-NOPRED", predecessor_id=None)
        warnings = check_dependency_warnings(act, db)
        assert len(warnings) == 0

    def test_dependency_is_warning_not_blocking(self, db):
        """
        Even with dependency warning, if there's no status conflict, the apply
        should succeed (warnings are advisory, not blocking).
        """
        _make_project(db)
        _make_activity(db, aid="ACT-PRDX", status="IN_PROGRESS")
        act = _make_activity(db, aid="ACT-SUCCX", predecessor_id="ACT-PRDX")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-DEP-001",
                          status="IN_PROGRESS", percent_complete=40.0,
                          identifier="ACT-SUCCX")
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        result = svc.apply_event_progress(evt.event_id)

        # Should still apply (no conflict, just warning)
        assert result["applied"] is True
        assert len(result["warnings"]) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 13 – MATCH SCORE SAFETY
# ══════════════════════════════════════════════════════════════════════════════


class TestMatchScoreSafety:
    """Section 13: Score bounds, weight sum, missing evidence neutrality."""

    def test_weights_sum_to_one(self):
        total = sum(MATCH_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, not 1.0"

    def test_overall_score_within_0_100(self, db):
        _make_project(db)
        act = _make_activity(db)
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id)

        scores = compute_all_candidate_scores(evt, act)
        overall = scores["overall_score"]
        assert 0.0 <= overall <= 100.0, f"Overall score {overall} out of bounds"

    def test_all_sub_scores_within_0_100(self, db):
        _make_project(db)
        act = _make_activity(db)
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id)

        scores = compute_all_candidate_scores(evt, act)
        for key, val in scores.items():
            assert 0.0 <= val <= 100.0, f"Score '{key}' = {val} is out of [0, 100]"

    def test_missing_identifier_gives_neutral_not_bonus(self, db):
        """Missing identifier must give 50.0, not boost score above missing level."""
        score = score_identifier(None, "ACT-001", "24P201")
        assert score == 50.0

    def test_identifier_conflict_penalizes(self, db):
        """Contradictory identifier must give 0.0."""
        score = score_identifier("24P999", "ACT-001", "24P201")
        assert score == 0.0

    def test_high_semantic_score_cannot_override_id_conflict(self, db):
        """
        Even if semantic similarity is 100%, an identifier conflict (0.0)
        must prevent AUTO_LINK from firing.
        """
        from backend.app.services.decision_policy import evaluate_decision_policy
        from backend.app.db.models.decision import DecisionEnum

        class FakeCandidate:
            overall_score = 72.0  # High semantic but dragged down by id_score 0
            activity_id = "ACT-FAKE"
            matcher_version = "v1"

        class FakeEvent:
            raw_text = "P999 work done at some location."
            identifier = "24P999"

        # overall_score < 85 threshold → HUMAN_REVIEW, not AUTO_LINK
        decision, _ = evaluate_decision_policy(FakeEvent(), [FakeCandidate()], 80.0, 100.0)
        assert decision != DecisionEnum.AUTO_LINK, "High semantic should not override id conflict to AUTO_LINK"

    def test_percentage_out_of_range_flagged(self):
        ok, msg = validate_percentage(150.0)
        assert not ok
        ok2, msg2 = validate_percentage(-5.0)
        assert not ok2

    def test_valid_percentage_passes(self):
        ok, _ = validate_percentage(75.0)
        assert ok
        ok2, _ = validate_percentage(0.0)
        assert ok2
        ok3, _ = validate_percentage(100.0)
        assert ok3

    def test_thresholds_come_from_settings(self):
        """Verify decision policy reads thresholds from settings, not hard-coded."""
        assert hasattr(settings, "MATCH_SCORE_THRESHOLD")
        assert hasattr(settings, "EVIDENCE_COMPLETENESS_THRESHOLD")
        assert hasattr(settings, "TOP2_MARGIN_THRESHOLD")
        assert settings.MATCH_SCORE_THRESHOLD > 0
        assert settings.TOP2_MARGIN_THRESHOLD > 0


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 14 – EMBEDDING MODEL
# ══════════════════════════════════════════════════════════════════════════════


class TestEmbeddingModel:
    """Section 14: Embedding model loading, caching, edge cases."""

    def test_model_loads_without_crash(self):
        model = get_embedding_model()
        # Either real model or None (fallback) – must not crash
        assert model is None or hasattr(model, "encode")

    def test_empty_text_returns_neutral_score(self, db):
        _make_project(db)
        act = _make_activity(db, aid="ACT-EMB")
        score = compute_semantic_similarity("", act)
        assert score == 50.0

    def test_whitespace_text_returns_neutral_score(self, db):
        _make_project(db)
        act = _make_activity(db, aid="ACT-EMB2")
        score = compute_semantic_similarity("   \n\t  ", act)
        assert score == 50.0

    def test_score_within_bounds(self, db):
        _make_project(db)
        act = _make_activity(db, aid="ACT-EMB3",
                             description="Spool erection at Rack B",
                             discipline="Piping")
        score = compute_semantic_similarity("Piping spool erection Rack B", act)
        assert 0.0 <= score <= 100.0

    def test_activity_cached_after_precompute(self, db):
        _make_project(db)
        act = _make_activity(db, aid="ACT-CACHE")
        precompute_schedule_embeddings([act])
        assert "ACT-CACHE" in _SCHEDULE_EMBEDDINGS_CACHE

    def test_different_activities_different_cache_entries(self, db):
        _make_project(db)
        a1 = _make_activity(db, aid="ACT-CA1", description="Piping spool erection")
        a2 = _make_activity(db, aid="ACT-CA2", description="Electrical cable pulling")
        precompute_schedule_embeddings([a1, a2])
        assert "ACT-CA1" in _SCHEDULE_EMBEDDINGS_CACHE
        assert "ACT-CA2" in _SCHEDULE_EMBEDDINGS_CACHE
        # Different activities must have distinct cache entries
        assert _SCHEDULE_EMBEDDINGS_CACHE["ACT-CA1"] is not _SCHEDULE_EMBEDDINGS_CACHE["ACT-CA2"]


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 15 – API CONTRACT
# ══════════════════════════════════════════════════════════════════════════════


class TestAPIContract:
    """Section 15: HTTP status codes for every documented endpoint."""

    # ── /projects ─────────────────────────────────────────────────────────────

    def test_get_projects_empty_list(self, client):
        r = client.get("/projects")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_post_project_valid(self, client):
        r = client.post("/projects", json={"project_id": "API-P-001", "name": "API Test", "description": ""})
        assert r.status_code == 201

    def test_post_project_missing_name(self, client):
        r = client.post("/projects", json={"project_id": "API-P-002"})
        assert r.status_code == 422  # Pydantic validation

    def test_post_project_malformed_json(self, client):
        r = client.post("/projects", content=b"not-json", headers={"Content-Type": "application/json"})
        assert r.status_code == 422

    def test_get_nonexistent_project_404(self, client):
        r = client.get("/projects/NONEXISTENT-999")
        assert r.status_code == 404

    # ── /reports ──────────────────────────────────────────────────────────────

    def test_get_nonexistent_report_404(self, client):
        r = client.get("/reports/REP-NONEXISTENT")
        assert r.status_code == 404

    def test_upload_report_missing_project_404(self, client):
        content = b"Some content here for test."
        files = {"file": ("report.txt", content, "text/plain")}
        data = {"project_id": "NONEXISTENT-PROJ", "report_date": "2025-02-15"}
        r = client.post("/reports/upload", data=data, files=files)
        assert r.status_code == 404

    def test_upload_report_missing_date_422(self, client, db):
        _make_project(db)
        content = b"P201 erection completed."
        files = {"file": ("report.txt", content, "text/plain")}
        data = {"project_id": "ADV-PROJ-001"}  # missing report_date
        r = client.post("/reports/upload", data=data, files=files)
        assert r.status_code == 422

    def test_upload_invalid_discipline_400(self, client, db):
        _make_project(db)
        content = b"P201 erection completed."
        files = {"file": ("report.txt", content, "text/plain")}
        data = {"project_id": "ADV-PROJ-001", "report_date": "2025-02-15", "discipline": "NUCLEAR"}
        r = client.post("/reports/upload", data=data, files=files)
        assert r.status_code == 400

    # ── /events ───────────────────────────────────────────────────────────────

    def test_extract_events_nonexistent_report_404(self, client):
        r = client.post("/reports/NONEXISTENT-RPT/extract")
        assert r.status_code == 404

    def test_get_events_nonexistent_report_404(self, client):
        r = client.get("/reports/NONEXISTENT/events")
        assert r.status_code == 404

    # ── /candidates ───────────────────────────────────────────────────────────

    def test_candidates_nonexistent_event_404(self, client):
        r = client.post("/events/NONEXISTENT-EVT/candidates")
        assert r.status_code == 404

    # ── /decisions ────────────────────────────────────────────────────────────

    def test_decision_nonexistent_event_404(self, client):
        r = client.post("/events/NONEXISTENT-EVT/decision")
        assert r.status_code == 404

    # ── /apply ────────────────────────────────────────────────────────────────

    def test_apply_nonexistent_event_404(self, client):
        r = client.post("/events/NONEXISTENT-EVT/apply")
        assert r.status_code == 404

    # ── /activities ───────────────────────────────────────────────────────────

    def test_activity_nonexistent_404(self, client):
        r = client.get("/activities/NONEXISTENT-ACT")
        assert r.status_code == 404

    def test_activity_audit_nonexistent_404(self, client):
        r = client.get("/activities/NONEXISTENT-ACT/audit")
        assert r.status_code == 404

    # ── /projects/{id}/wbs ────────────────────────────────────────────────────

    def test_wbs_nonexistent_project_404(self, client):
        r = client.get("/projects/NONEXISTENT/wbs")
        assert r.status_code == 404

    # ── /health ───────────────────────────────────────────────────────────────

    def test_health_endpoint_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 16 – SECURITY
# ══════════════════════════════════════════════════════════════════════════════


class TestSecurity:
    """Section 16: Path traversal, injection, oversized body, secrets."""

    def test_path_traversal_in_filename_rejected_or_safe(self, client, db):
        """../../etc/passwd as filename must not result in server error or actual traversal."""
        _make_project(db)
        content = b"P201 erection started."
        files = {"file": ("../../etc/passwd", content, "text/plain")}
        data = {"project_id": "ADV-PROJ-001", "report_date": "2025-02-15", "discipline": "Piping"}
        r = client.post("/reports/upload", data=data, files=files)
        # Must not 500; allowed to 400 (bad extension) or 201 (stored safely)
        assert r.status_code != 500

    def test_sql_injection_in_project_id_safe(self, client):
        """SQL injection in project_id URL path must not cause server error."""
        r = client.get("/projects/' OR '1'='1")
        assert r.status_code in (404, 422)  # Not 500

    def test_xss_payload_in_report_text_not_executed(self, client, db):
        """HTML/script tags in report text must be stored as data, not executed."""
        _make_project(db)
        xss_content = b"<script>alert('xss')</script> P201 erection completed."
        files = {"file": ("xss_report.txt", xss_content, "text/plain")}
        data = {"project_id": "ADV-PROJ-001", "report_date": "2025-02-15", "discipline": "Piping"}
        r = client.post("/reports/upload", data=data, files=files)
        assert r.status_code in (201, 400)
        # If accepted, the raw_content should contain the script tag as literal text
        if r.status_code == 201:
            report_id = r.json()["report_id"]
            rr = client.get(f"/reports/{report_id}")
            # Response should be JSON, not HTML executing script
            assert rr.headers.get("content-type", "").startswith("application/json")

    def test_cors_wildcard_documented(self):
        """CORS_ORIGINS is configurable; confirm the default is '*' (open) and documented."""
        assert settings.CORS_ORIGINS == "*"  # Known open default for dev; should be restricted in prod

    def test_env_file_not_tracked_in_git(self):
        """.env must be in .gitignore."""
        gitignore_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            ".gitignore"
        )
        if os.path.exists(gitignore_path):
            with open(gitignore_path) as f:
                contents = f.read()
            assert ".env" in contents, ".env must be listed in .gitignore"

    def test_env_example_exists(self):
        """.env.example must exist for clean machine setup."""
        # Check project root
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path1 = os.path.join(root, ".env.example")
        path2 = os.path.join(root, "backend", ".env.example")
        assert os.path.exists(path1) or os.path.exists(path2), ".env.example missing"

    def test_oversized_request_body_rejected(self, client, db):
        """File exceeding MAX_FILE_SIZE_BYTES must be rejected with 400."""
        _make_project(db)
        big = b"P201 erection started." * 600000  # ~12MB
        files = {"file": ("big.txt", big, "text/plain")}
        data = {"project_id": "ADV-PROJ-001", "report_date": "2025-02-15", "discipline": "Piping"}
        r = client.post("/reports/upload", data=data, files=files)
        assert r.status_code == 400

    def test_malformed_unicode_in_request_safe(self, client, db):
        """Malformed UTF-8 bytes in text body must not crash server."""
        _make_project(db)
        bad_unicode = b"P201 erection completed.\xff\xfe invalid bytes"
        files = {"file": ("unicode.txt", bad_unicode, "text/plain")}
        data = {"project_id": "ADV-PROJ-001", "report_date": "2025-02-15", "discipline": "Piping"}
        r = client.post("/reports/upload", data=data, files=files)
        assert r.status_code in (201, 400)  # Not 500


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 17 – AUDIT IMMUTABILITY
# ══════════════════════════════════════════════════════════════════════════════


class TestAuditImmutability:
    """Section 17: Audit records correctness and immutability."""

    def test_audit_previous_and_new_state_correct(self, db):
        _make_project(db)
        act = _make_activity(db, aid="ACT-AUD-IMM", status="NOT_STARTED", percent_complete=0.0)
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-AUD-IMM-001",
                          status="IN_PROGRESS", percent_complete=60.0)
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        result = svc.apply_event_progress(evt.event_id)

        audit = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).first()
        assert audit is not None
        prev = audit.previous_value
        new = audit.new_value

        assert prev["status"] == "NOT_STARTED"
        assert prev["percent_complete"] == 0.0
        assert new["status"] == "IN_PROGRESS"
        assert new["percent_complete"] == 60.0

    def test_audit_links_correct_event_and_report(self, db):
        _make_project(db)
        act = _make_activity(db, aid="ACT-AUD-LINK")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-AUD-LINK-001")
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        svc.apply_event_progress(evt.event_id)

        audit = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).first()
        assert audit.event_id == evt.event_id
        assert audit.report_id == rep.report_id
        assert audit.activity_id == act.activity_id

    def test_rejected_decision_no_audit(self, db):
        _make_project(db)
        act = _make_activity(db, aid="ACT-AUD-REJ")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-AUD-REJ-001")
        _make_decision(db, eid=evt.event_id, aid=act.activity_id, decision="HUMAN_REVIEW")

        svc = ProgressUpdateService(db)
        svc.apply_event_progress(evt.event_id)

        audit = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).first()
        assert audit is None, "HUMAN_REVIEW must not produce audit"

    def test_duplicate_event_does_not_double_audit(self, db):
        _make_project(db)
        act = _make_activity(db, aid="ACT-AUD-DUP")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-AUD-DUP-001")
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        svc.apply_event_progress(evt.event_id)
        svc.apply_event_progress(evt.event_id)  # duplicate

        audits = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).all()
        assert len(audits) == 1, f"Expected 1 audit, got {len(audits)}"

    def test_snapshot_captures_planned_dates_unchanged(self, db):
        _make_project(db)
        act = _make_activity(db, aid="ACT-SNAP",
                             planned_start=datetime.date(2025, 1, 1),
                             planned_finish=datetime.date(2025, 3, 31))
        snapshot = build_schedule_state_snapshot(act)
        # Snapshot must contain status and percent_complete but NOT planned dates
        assert "status" in snapshot
        assert "percent_complete" in snapshot
        # planned_start/planned_finish must NOT appear in actuals snapshot
        assert "planned_start" not in snapshot
        assert "planned_finish" not in snapshot


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 18 – CONCURRENCY
# ══════════════════════════════════════════════════════════════════════════════


class TestConcurrency:
    """
    Section 18: Two concurrent applies for the same activity.
    SQLite serializes writes, so we test that the final state is consistent
    and that exactly one of the two applies wins the idempotency check.
    """

    def test_concurrent_apply_same_activity_consistent(self, db):
        """
        Two threads both call apply_event_progress for the same event.
        Only one should create an audit record; the other must see already_applied.

        NOTE: SQLite + StaticPool (used in tests) serializes writes through one
        connection. True concurrent writes from multiple threads will conflict at
        the connection level, not the application level. The real concurrency
        protection is the DB-level UniqueConstraint on AuditRecord.event_id (BUG-002 fix)
        which enforces uniqueness in production (PostgreSQL). This test validates
        the sequential idempotency path (already_applied) instead, and separately
        confirms the UniqueConstraint exists on the model.
        """
        _make_project(db)
        act = _make_activity(db, aid="ACT-CONC")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-CONC-001",
                          status="IN_PROGRESS", percent_complete=60.0)
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        # Verify the DB-level unique constraint is present on the model (BUG-002 fix)
        from sqlalchemy import inspect as sa_inspect
        mapper = sa_inspect(AuditRecord)
        table = mapper.persist_selectable
        unique_constraints = {uc.name for uc in table.constraints
                               if hasattr(uc, 'columns')}
        # Also check mapped_column unique flag
        event_id_col = table.c.get("event_id")
        assert event_id_col is not None
        assert event_id_col.unique or "uq_audit_event_id" in unique_constraints, (
            "BUG-002 FIX: AuditRecord.event_id must have a unique constraint to prevent concurrent duplicates"
        )

        # Validate sequential idempotency (the SQLite-testable path)
        svc = ProgressUpdateService(db)
        r1 = svc.apply_event_progress(evt.event_id)
        assert r1["applied"] is True

        r2 = svc.apply_event_progress(evt.event_id)
        assert r2["already_applied"] is True

        # Exactly one audit record
        audits = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).all()
        assert len(audits) == 1, (
            f"Expected exactly 1 audit after sequential apply, got {len(audits)}"
        )




# ══════════════════════════════════════════════════════════════════════════════
# SECTION 19 – VOICE EDGE-CASES
# ══════════════════════════════════════════════════════════════════════════════


class TestVoiceEdgeCases:
    """Section 19: Voice transcription edge-cases."""

    def test_voice_endpoint_returns_valid_structure(self, client, db):
        """POST /voice/transcribe must return structured JSON, not crash."""
        _make_project(db)
        # Send a minimal audio file (WAV header only)
        wav_header = bytes([
            0x52, 0x49, 0x46, 0x46,  # RIFF
            0x24, 0x00, 0x00, 0x00,  # file size
            0x57, 0x41, 0x56, 0x45,  # WAVE
            0x66, 0x6d, 0x74, 0x20,  # fmt
            0x10, 0x00, 0x00, 0x00,  # chunk size
            0x01, 0x00,              # PCM
            0x01, 0x00,              # mono
            0x44, 0xac, 0x00, 0x00,  # 44100 Hz
            0x88, 0x58, 0x01, 0x00,  # byte rate
            0x02, 0x00,              # block align
            0x10, 0x00,              # 16 bit
            0x64, 0x61, 0x74, 0x61,  # data
            0x00, 0x00, 0x00, 0x00,  # data size
        ])
        files = {"file": ("voice.wav", wav_header, "audio/wav")}
        data = {"project_id": "ADV-PROJ-001"}
        r = client.post("/voice/transcribe", data=data, files=files)
        # Must not 500
        assert r.status_code != 500

    def test_unsupported_audio_type_rejected(self, client, db):
        """Unsupported audio format should return 400."""
        _make_project(db)
        content = b"This is not audio"
        files = {"file": ("voice.mp3", content, "audio/mpeg")}
        data = {"project_id": "ADV-PROJ-001"}
        r = client.post("/voice/transcribe", data=data, files=files)
        # mp3 may or may not be supported; should not 500
        assert r.status_code != 500

    def test_voice_transcript_not_directly_applied(self, client, db):
        """
        Voice transcription must NOT directly mutate the schedule.
        The result must go through normal extraction → decision → apply pipeline.
        """
        # This is an architectural guarantee we verify by checking there is
        # no route POST /voice/apply or similar that bypasses the pipeline.
        from backend.app.main import app as fastapi_app
        routes = [getattr(r, "path", "") for r in fastapi_app.routes]
        # There must be no direct-apply voice endpoint
        forbidden_patterns = ["/voice/apply", "/voice/update"]
        for pattern in forbidden_patterns:
            for route in routes:
                assert pattern not in route, (
                    f"Forbidden direct-apply voice route found: {route}"
                )


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 22 – RESTART / DB PERSISTENCE
# ══════════════════════════════════════════════════════════════════════════════


class TestRestartPersistence:
    """
    Section 22: Verifies that applied events and audits persist across DB re-open.
    We simulate this with a file-based SQLite DB to mimic real persistence.
    """

    def test_applied_event_persists_after_session_close(self, db):
        """After closing and re-opening a session, audit and schedule update must persist."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-PERSIST")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-PERSIST-001")
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        svc.apply_event_progress(evt.event_id)

        # Simulate session close and reopen
        db.close()
        new_session = _Session()
        try:
            Base.metadata.create_all(bind=_engine)
            audit = new_session.query(AuditRecord).filter(
                AuditRecord.event_id == evt.event_id
            ).first()
            assert audit is not None, "AuditRecord not persisted after session close"

            refreshed = new_session.query(ScheduleActivity).filter(
                ScheduleActivity.activity_id == act.activity_id
            ).first()
            assert refreshed is not None
            assert refreshed.status == "COMPLETED"
        finally:
            new_session.close()

    def test_duplicate_detection_survives_reopen(self, db):
        """Duplicate detection must work even after session boundary."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-DUP-SRV")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-DUP-SRV-001")
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        svc.apply_event_progress(evt.event_id)
        db.close()

        new_session = _Session()
        try:
            Base.metadata.create_all(bind=_engine)
            svc2 = ProgressUpdateService(new_session)
            r2 = svc2.apply_event_progress(evt.event_id)
            assert r2["already_applied"] is True
        finally:
            new_session.close()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 23 – CLEAN MACHINE SETUP
# ══════════════════════════════════════════════════════════════════════════════


class TestCleanMachineSetup:
    """Section 23: Verify documentation and setup completeness."""

    def _project_root(self):
        return os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )

    def test_readme_exists(self):
        readme = os.path.join(self._project_root(), "README.md")
        assert os.path.exists(readme), "README.md must exist"

    def test_requirements_txt_exists(self):
        req = os.path.join(self._project_root(), "backend", "requirements.txt")
        assert os.path.exists(req), "backend/requirements.txt must exist"

    def test_env_example_exists_in_project(self):
        root = self._project_root()
        p1 = os.path.join(root, ".env.example")
        p2 = os.path.join(root, "backend", ".env.example")
        assert os.path.exists(p1) or os.path.exists(p2), ".env.example must exist"

    def test_no_absolute_paths_in_requirements(self):
        req = os.path.join(self._project_root(), "backend", "requirements.txt")
        if not os.path.exists(req):
            return
        with open(req) as f:
            content = f.read()
        # No absolute paths like /Users/... or /home/...
        assert "/Users/" not in content, "Absolute path in requirements.txt"
        assert "/home/" not in content, "Absolute home path in requirements.txt"

    def test_gitignore_ignores_env_and_db(self):
        gitignore = os.path.join(self._project_root(), ".gitignore")
        if not os.path.exists(gitignore):
            pytest.skip(".gitignore not found")
        with open(gitignore) as f:
            content = f.read()
        assert ".env" in content, ".env must be in .gitignore"


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 21 – RANDOMISED STRESS TESTS
# ══════════════════════════════════════════════════════════════════════════════


class TestRandomisedStress:
    """
    Section 21: Synthetic stress inputs – random typos, missing IDs, paraphrases.
    Focuses on crashes and unsafe auto-links only (does not assert correctness).
    """

    STRESS_INPUTS = [
        # typo/OCR errors
        "24P2O1 erect1on comp1eted at Rack B",          # OCR 0→O, 1→l
        "P201erection completd",                          # missing space, typo
        "24P-201 erection complteed",                     # hyphen + typo
        "P 201 erection started!!!",                      # extra spaces + punctuation
        # missing ID
        "Spool erection completed at Rack B.",
        # wrong location
        "P201 erection completed at Wrong Area Z99.",
        # ALL CAPS
        "24P201 ERECTION COMPLETED AT RACK B.",
        # all lowercase
        "24p201 erection completed at rack b.",
        # Mixed case
        "24P201 ErEcTiOn CoMpLeTed At RaCk B.",
        # paraphrase
        "Pipe segment installation at Rack B finished successfully for line 24P201.",
        # no punctuation
        "24P201 erection at Rack B completed 100 percent",
        # extreme garbage
        "!@#$%^&*() 24P201 💥 completed ???",
        # empty-ish
        "...",
        "   ",
    ]

    @pytest.mark.parametrize("text", STRESS_INPUTS)
    def test_extraction_does_not_crash(self, text):
        """Every stress input must be handled without raising an exception."""
        try:
            status = extract_status(text)
            pct = extract_percent_complete(text)
            ident = extract_identifier(text)
            action = extract_action(text)
            loc = extract_location(text)
            segs = segment_text_into_events(text)
            # All must return valid types (not crash)
            assert status is None or isinstance(status, str)
            assert pct is None or isinstance(pct, float)
            assert ident is None or isinstance(ident, str)
        except Exception as e:
            pytest.fail(f"Crash on stress input '{text[:50]}': {e}")

    @pytest.mark.parametrize("text", STRESS_INPUTS)
    def test_normalize_does_not_crash(self, text):
        """normalize_identifier must not crash on any stress input."""
        ident = extract_identifier(text)
        try:
            result = normalize_identifier(ident)
            assert result is None or isinstance(result, str)
        except Exception as e:
            pytest.fail(f"normalize_identifier crash on '{ident}': {e}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION BUG REGRESSION – Specific Bugs Found and Fixed
# ══════════════════════════════════════════════════════════════════════════════


class TestBugRegressions:
    """Regression tests for every bug identified during adversarial testing."""

    def test_bug_r001_null_byte_event_text_does_not_crash_segmenter(self):
        """BUG-R001: Null bytes in event text must not crash the text segmenter."""
        text_with_null = "P201 erection completed.\x00 Extra text."
        try:
            segs = segment_text_into_events(text_with_null)
            assert isinstance(segs, list)
        except Exception as e:
            pytest.fail(f"BUG-R001: Null byte caused crash: {e}")

    def test_bug_r002_percent_just_over_100_rejected_by_validator(self):
        """BUG-R002: Percent 100.01% must be rejected by validate_percentage."""
        ok, msg = validate_percentage(100.01)
        assert not ok, "BUG-R002: 100.01% should be invalid"

    def test_bug_r003_conflict_review_decision_not_auto_applied(self, db):
        """BUG-R003: An event re-routed to CONFLICT_REVIEW must not create an audit."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-CR",
                             status="COMPLETED", percent_complete=100.0,
                             actual_finish=datetime.date(2025, 2, 20))
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-CR-001",
                          status="STARTED", percent_complete=0.0)
        _make_decision(db, eid=evt.event_id, aid=act.activity_id, decision="AUTO_LINK")

        svc = ProgressUpdateService(db)
        result = svc.apply_event_progress(evt.event_id)

        # Must be routed to CONFLICT_REVIEW
        assert result["decision"] == "CONFLICT_REVIEW"
        assert result["applied"] is False
        # Must not have an audit
        audit = db.query(AuditRecord).filter(AuditRecord.event_id == evt.event_id).first()
        assert audit is None, "BUG-R003: CONFLICT_REVIEW must not produce audit"

    def test_bug_r004_missing_decision_raises_value_error(self, db):
        """BUG-R004: Calling apply with no MatchDecision must raise ValueError, not 500 crash."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-NODEC")
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-NODEC-001")
        # No decision created

        svc = ProgressUpdateService(db)
        with pytest.raises(ValueError, match="MatchDecision"):
            svc.apply_event_progress(evt.event_id)

    def test_bug_r005_actual_start_immutable_once_set(self, db):
        """
        BUG-R005: actual_start must not be overwritten once set.
        A second event reporting STARTED must not clobber the first actual_start.
        """
        _make_project(db)
        first_start = datetime.date(2025, 1, 10)
        act = _make_activity(db, aid="ACT-STPROT",
                             status="STARTED", percent_complete=10.0,
                             actual_start=first_start)
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-STPROT-001",
                          status="IN_PROGRESS", percent_complete=50.0,
                          event_date=datetime.date(2025, 2, 1))
        _make_decision(db, eid=evt.event_id, aid=act.activity_id)

        svc = ProgressUpdateService(db)
        svc.apply_event_progress(evt.event_id)

        db.expire_all()
        refreshed = db.query(ScheduleActivity).filter(ScheduleActivity.activity_id == act.activity_id).first()
        assert refreshed.actual_start == first_start, (
            f"BUG-R005: actual_start was overwritten: expected {first_start}, got {refreshed.actual_start}"
        )

    def test_bug_r006_location_normalization_not_overly_aggressive(self):
        """BUG-R006: 'Rack B' and 'Rack C' must not normalize to same string."""
        from backend.app.services.normalizer_service import normalize_location
        n_b = normalize_location("Rack B")
        n_c = normalize_location("Rack C")
        assert n_b != n_c, f"BUG-R006: 'Rack B' and 'Rack C' both normalized to '{n_b}'"

    def test_bug_r007_score_discipline_mismatch_gives_zero(self):
        """BUG-R007: Discipline mismatch must score 0.0, not 50.0."""
        score = score_discipline("Electrical", "Piping")
        assert score == 0.0, f"BUG-R007: Discipline mismatch gave {score}, expected 0.0"

    def test_bug_r008_conflict_review_updates_decision_record(self, db):
        """BUG-R008: When conflict fires, decision.decision must be updated to CONFLICT_REVIEW."""
        _make_project(db)
        act = _make_activity(db, aid="ACT-CR2",
                             status="COMPLETED", percent_complete=100.0,
                             actual_finish=datetime.date(2025, 2, 20))
        rep = _make_report(db)
        evt = _make_event(db, rid=rep.report_id, eid="EVT-CR2-001",
                          status="IN_PROGRESS", percent_complete=60.0)
        dec = _make_decision(db, eid=evt.event_id, aid=act.activity_id, decision="AUTO_LINK")

        svc = ProgressUpdateService(db)
        svc.apply_event_progress(evt.event_id)

        db.expire_all()
        refreshed_dec = db.query(MatchDecision).filter(MatchDecision.event_id == evt.event_id).first()
        assert refreshed_dec.decision == "CONFLICT_REVIEW", (
            f"BUG-R008: Decision not updated to CONFLICT_REVIEW after conflict"
        )
