import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from backend.app.config import settings
from backend.app.db.models.transcription import Transcription
from backend.app.db.models.report import SourceReport
from backend.app.schemas.event import ExtractedEventResponse
from backend.app.services.hash_service import calculate_sha256
from backend.app.services.audio_validator import validate_audio_file_content, AudioValidationError
from backend.app.services.transcription_service import TranscriptionService
from backend.app.services.event_extraction_service import EventExtractionService

def transcribe_uploaded_audio(
    filename: str,
    file_bytes: bytes,
    project_id: Optional[str],
    db: Session
) -> Transcription:
    """
    Validates uploaded audio, saves temporary audio file, executes local STT transcription,
    records immutable Transcription DB provenance, and cleans up temporary file.
    """
    val = validate_audio_file_content(filename, file_bytes)
    clean_filename = val["filename"]
    file_hash = calculate_sha256(file_bytes)
    file_size = val["file_size"]

    audio_dir = Path(settings.AUDIO_UPLOAD_DIR)
    audio_dir.mkdir(parents=True, exist_ok=True)
    temp_path = audio_dir / f"{file_hash[:12]}_{clean_filename}"
    
    trans_record = None

    try:
        with open(temp_path, "wb") as f:
            f.write(file_bytes)

        trans_record = Transcription(
            project_id=project_id,
            filename=clean_filename,
            file_hash=file_hash,
            file_size=file_size,
            status="PROCESSING",
            model_name=getattr(settings, "WHISPER_MODEL_SIZE", "tiny"),
            created_at=datetime.now(timezone.utc)
        )
        db.add(trans_record)
        db.commit()
        db.refresh(trans_record)

        stt_service = TranscriptionService()
        if not stt_service.is_available:
            trans_record.status = "FAILED"
            trans_record.error_message = "Local Speech-to-Text engine unavailable."
            db.commit()
            raise AudioValidationError(
                message="Local Speech-to-Text engine unavailable.",
                code="STT_ENGINE_UNAVAILABLE"
            )

        res = stt_service.transcribe_audio_file(str(temp_path))

        trans_record.transcript = res["transcript"]
        trans_record.language = res.get("language", "en")
        trans_record.duration_seconds = res.get("duration_seconds")
        trans_record.model_name = res.get("model", trans_record.model_name)
        trans_record.status = "COMPLETED"
        db.commit()
        db.refresh(trans_record)
        return trans_record

    except Exception as e:
        if trans_record:
            trans_record.status = "FAILED"
            trans_record.error_message = str(e)
            db.commit()
        if isinstance(e, AudioValidationError):
            raise e
        raise AudioValidationError(
            message=f"Transcription failed: {str(e)}",
            code="TRANSCRIPTION_FAILED"
        )
    finally:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass

def update_transcription_text(transcription_id: str, new_transcript: str, db: Session) -> Transcription:
    """Updates/corrects transcript text for a transcription record."""
    trans = db.query(Transcription).filter(Transcription.transcription_id == transcription_id).first()
    if not trans:
        raise ValueError(f"Transcription with ID '{transcription_id}' not found.")

    trans.transcript = new_transcript.strip()
    if trans.status == "FAILED":
        trans.status = "COMPLETED"
        trans.error_message = None
    db.commit()
    db.refresh(trans)
    return trans

def process_transcription_to_events(
    transcription_id: str,
    project_id: Optional[str],
    db: Session
) -> Dict[str, Any]:
    """
    Submits a completed voice transcript into the existing text event extraction pipeline.
    Creates SourceReport and invokes EventExtractionService.
    """
    trans = db.query(Transcription).filter(Transcription.transcription_id == transcription_id).first()
    if not trans:
        raise ValueError(f"Transcription with ID '{transcription_id}' not found.")

    if not trans.transcript:
        raise ValueError(f"Transcription '{transcription_id}' has no transcript text to process.")

    target_project_id = project_id or trans.project_id or "PROJ-ALPHA"
    file_bytes = trans.transcript.encode("utf-8")
    report_hash = calculate_sha256(file_bytes)

    report_date = trans.created_at.date() if trans.created_at else datetime.now(timezone.utc).date()

    # Check for existing report or create synthetic SourceReport for voice transcript
    existing_rep = db.query(SourceReport).filter(SourceReport.file_hash == report_hash).first()
    if not existing_rep:
        report_dir = Path(settings.UPLOAD_DIR)
        report_dir.mkdir(parents=True, exist_ok=True)
        stored_path = report_dir / f"{report_hash[:12]}_voice_{trans.transcription_id}.txt"
        with open(stored_path, "w", encoding="utf-8") as f:
            f.write(str(trans.transcript))

        rep = SourceReport(
            report_id=f"REP-VOICE-{trans.transcription_id}",
            project_id=target_project_id,
            filename=f"voice_{trans.filename}.txt",
            source_type="TXT",
            report_date=report_date,
            file_hash=report_hash,
            file_size=len(file_bytes),
            stored_path=str(stored_path),
            raw_content=trans.transcript,
            processing_status="VALIDATED"
        )
        db.add(rep)
        db.commit()
        db.refresh(rep)
        report_id = rep.report_id
    else:
        if not existing_rep.raw_content:
            existing_rep.raw_content = trans.transcript
            db.commit()
        report_id = existing_rep.report_id

    extraction_service = EventExtractionService(db)
    updated_rep, events = extraction_service.extract_events_from_report(str(report_id))

    event_responses = [ExtractedEventResponse.model_validate(evt) for evt in events]

    return {
        "transcription_id": transcription_id,
        "transcript": trans.transcript,
        "report_id": updated_rep.report_id,
        "processing_status": updated_rep.processing_status,
        "event_count": len(event_responses),
        "events": event_responses
    }
