import os
import io
import struct
import pytest
from unittest.mock import patch
from backend.app.services.baseline_importer import BaselineImporter
from backend.app.services.transcription_service import TranscriptionService
from backend.app.services.audio_validator import validate_audio_file_content, AudioValidationError, sanitize_audio_filename
from backend.app.db.models.transcription import Transcription
from backend.app.db.models.activity import ScheduleActivity

@pytest.fixture(autouse=True)
def setup_baseline_data(db_session):
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    dataset_path = os.path.join(project_root, "dataset", "01_baseline_schedule.xlsx")
    if os.path.exists(dataset_path):
        importer = BaselineImporter(db_session)
        importer.import_excel_baseline(dataset_path)

def generate_minimal_wav_bytes(duration_sec=1, sample_rate=16000) -> bytes:
    """Generates a valid 16kHz 16-bit mono PCM WAV file in bytes for testing."""
    num_samples = int(duration_sec * sample_rate)
    data_size = num_samples * 2
    header = bytearray()
    header.extend(b"RIFF")
    header.extend(struct.pack("<I", 36 + data_size))
    header.extend(b"WAVEfmt ")
    header.extend(struct.pack("<I", 16))
    header.extend(struct.pack("<H", 1)) # PCM
    header.extend(struct.pack("<H", 1)) # Mono
    header.extend(struct.pack("<I", sample_rate))
    header.extend(struct.pack("<I", sample_rate * 2))
    header.extend(struct.pack("<H", 2)) # Block align
    header.extend(struct.pack("<H", 16)) # Bits per sample
    header.extend(b"data")
    header.extend(struct.pack("<I", data_size))
    pcm_data = b"\x00\x00" * num_samples
    return bytes(header + pcm_data)

def test_1_unsupported_audio_extension_rejection():
    with pytest.raises(AudioValidationError) as exc_info:
        validate_audio_file_content("document.pdf", b"pdf content")
    assert exc_info.value.code == "UNSUPPORTED_AUDIO_FORMAT"

def test_2_empty_audio_rejection():
    with pytest.raises(AudioValidationError) as exc_info:
        validate_audio_file_content("empty.wav", b"")
    assert exc_info.value.code == "EMPTY_AUDIO_FILE"

def test_3_oversized_audio_rejection():
    large_bytes = b"\x00" * (11 * 1024 * 1024)
    with pytest.raises(AudioValidationError) as exc_info:
        validate_audio_file_content("large.wav", large_bytes)
    assert exc_info.value.code == "AUDIO_TOO_LARGE"

def test_4_path_traversal_filename_sanitization():
    clean = sanitize_audio_filename("../../etc/malicious.wav")
    assert clean == "malicious.wav"
    assert "../" not in clean

def test_5_singleton_model_loading():
    s1 = TranscriptionService()
    s2 = TranscriptionService()
    assert s1 is s2

def test_6_api_unsupported_audio_format(client):
    res = client.post(
        "/voice/transcribe",
        files={"file": ("test.pdf", b"pdf data", "application/pdf")}
    )
    assert res.status_code == 400

def test_7_api_transcribe_mocked_success(client, db_session):
    wav_bytes = generate_minimal_wav_bytes()
    mock_trans_result = {
        "transcript": "24P201 spool erection started near Rack B",
        "language": "en",
        "duration_seconds": 2.5,
        "model": "tiny",
        "processing_time_ms": 150
    }

    with patch.object(TranscriptionService, "is_available", True), \
         patch.object(TranscriptionService, "transcribe_audio_file", return_value=mock_trans_result):
        res = client.post(
            "/voice/transcribe",
            data={"project_id": "PROJ-ALPHA"},
            files={"file": ("field_report.wav", wav_bytes, "audio/wav")}
        )
        assert res.status_code == 201
        body = res.json()
        assert body["status"] == "COMPLETED"
        assert body["transcript"] == "24P201 spool erection started near Rack B"
        assert body["language"] == "en"

def test_8_api_transcript_correction_patch(client, db_session):
    trx = Transcription(
        filename="speech.wav",
        file_hash="hash12345",
        file_size=500,
        status="COMPLETED",
        transcript="24P201 spool erection started"
    )
    db_session.add(trx)
    db_session.commit()

    res = client.patch(
        f"/transcriptions/{trx.transcription_id}",
        json={"transcript": "24P201 spool erection started near Rack B."}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["transcript"] == "24P201 spool erection started near Rack B."

def test_9_voice_pipeline_integration_no_direct_schedule_mutation(client, db_session):
    trx = Transcription(
        filename="speech.wav",
        file_hash="hash67890",
        file_size=600,
        status="COMPLETED",
        transcript="24P201 spool erection started near Rack B."
    )
    db_session.add(trx)
    db_session.commit()

    # Process transcript into existing text event extraction pipeline
    res = client.post(
        f"/transcriptions/{trx.transcription_id}/process",
        params={"project_id": "PROJ-ALPHA"}
    )
    assert res.status_code == 200
    body = res.json()
    assert body["event_count"] > 0
    first_event = body["events"][0]
    assert first_event["identifier"] == "24P201"
    assert first_event["status"] == "STARTED"

    # CRITICAL: Verify ScheduleActivity actual progress was NOT directly mutated by voice processing alone
    act = db_session.query(ScheduleActivity).filter(ScheduleActivity.activity_id == "ACT-ALPHA-020").first()
    if act:
        assert act.status == "NOT_STARTED"
