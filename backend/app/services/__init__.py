from backend.app.services.baseline_importer import BaselineImporter
from backend.app.services.validation import (
    validate_date_range,
    validate_percent_complete,
    validate_status,
    validate_duplicate_activity_ids,
    ValidationError
)
from backend.app.services.hash_service import calculate_sha256
from backend.app.services.storage_service import save_uploaded_file, delete_uploaded_file
from backend.app.services.file_validator import validate_file_content, ReportValidationError
from backend.app.services.report_ingestion_service import ReportIngestionService
from backend.app.services.text_segmenter import segment_text_into_events
from backend.app.services.field_extractors import (
    extract_status,
    extract_percent_complete,
    extract_identifier,
    extract_action,
    extract_object,
    extract_location,
    extract_quantity_and_unit,
    extract_explicit_date
)
from backend.app.services.event_extraction_service import EventExtractionService
from backend.app.services.normalizer_service import (
    normalize_identifier,
    normalize_action,
    normalize_object,
    normalize_location
)
from backend.app.services.embedding_service import precompute_schedule_embeddings, compute_semantic_similarity
from backend.app.services.candidate_scorer import compute_all_candidate_scores, MATCH_WEIGHTS
from backend.app.services.candidate_generator_service import CandidateGeneratorService
from backend.app.services.evidence_service import calculate_evidence_completeness, derive_evidence_reasons
from backend.app.services.decision_policy import (
    evaluate_decision_policy,
    SCORING_POLICY_VERSION
)
# Threshold constants are now read from settings at runtime (configurable via .env)
from backend.app.config import settings as _settings
MATCH_SCORE_THRESHOLD = _settings.MATCH_SCORE_THRESHOLD
EVIDENCE_COMPLETENESS_THRESHOLD = _settings.EVIDENCE_COMPLETENESS_THRESHOLD
TOP2_MARGIN_THRESHOLD = _settings.TOP2_MARGIN_THRESHOLD
from backend.app.services.decision_service import DecisionService
from backend.app.services.state_validator import (
    validate_state_transition,
    validate_date_ordering,
    validate_percentage,
    check_dependency_warnings
)
from backend.app.services.conflict_service import detect_schedule_conflicts
from backend.app.services.audit_service import build_schedule_state_snapshot, record_schedule_audit
from backend.app.services.progress_update_service import ProgressUpdateService
from backend.app.services.dashboard_service import get_project_dashboard_summary
from backend.app.services.human_review_service import process_human_review_decision
from backend.app.services.timeline_service import get_project_timeline_data
from backend.app.services.audio_validator import validate_audio_file_content, AudioValidationError, sanitize_audio_filename
from backend.app.services.transcription_service import TranscriptionService
from backend.app.services.voice_service import (
    transcribe_uploaded_audio,
    update_transcription_text,
    process_transcription_to_events
)

__all__ = [
    "BaselineImporter",
    "validate_date_range",
    "validate_percent_complete",
    "validate_status",
    "validate_duplicate_activity_ids",
    "ValidationError",
    "calculate_sha256",
    "save_uploaded_file",
    "delete_uploaded_file",
    "validate_file_content",
    "ReportValidationError",
    "ReportIngestionService",
    "segment_text_into_events",
    "extract_status",
    "extract_percent_complete",
    "extract_identifier",
    "extract_action",
    "extract_object",
    "extract_location",
    "extract_quantity_and_unit",
    "extract_explicit_date",
    "EventExtractionService",
    "normalize_identifier",
    "normalize_action",
    "normalize_object",
    "normalize_location",
    "precompute_schedule_embeddings",
    "compute_semantic_similarity",
    "compute_all_candidate_scores",
    "MATCH_WEIGHTS",
    "CandidateGeneratorService",
    "calculate_evidence_completeness",
    "derive_evidence_reasons",
    "evaluate_decision_policy",
    "MATCH_SCORE_THRESHOLD",
    "EVIDENCE_COMPLETENESS_THRESHOLD",
    "TOP2_MARGIN_THRESHOLD",
    "SCORING_POLICY_VERSION",
    "DecisionService",
    "validate_state_transition",
    "validate_date_ordering",
    "validate_percentage",
    "check_dependency_warnings",
    "detect_schedule_conflicts",
    "build_schedule_state_snapshot",
    "record_schedule_audit",
    "ProgressUpdateService",
    "get_project_dashboard_summary",
    "process_human_review_decision",
    "get_project_timeline_data",
    "validate_audio_file_content",
    "AudioValidationError",
    "sanitize_audio_filename",
    "TranscriptionService",
    "transcribe_uploaded_audio",
    "update_transcription_text",
    "process_transcription_to_events"
]
