from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.db.models.transcription import Transcription
from backend.app.schemas.voice import TranscriptionResponse, TranscriptUpdateRequest, VoiceProcessResponse
from backend.app.services.audio_validator import AudioValidationError
from backend.app.services.voice_service import (
    transcribe_uploaded_audio,
    update_transcription_text,
    process_transcription_to_events
)

router = APIRouter(tags=["Voice Input & Speech-To-Text"])

@router.post("/voice/transcribe", response_model=TranscriptionResponse, status_code=status.HTTP_201_CREATED)
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    project_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Uploads a spoken audio file (.wav, .mp3, .m4a, .webm, .ogg), validates format and size,
    executes local CPU-first Speech-to-Text transcription, records DB provenance, and returns transcript.
    """
    file_bytes = await file.read()
    try:
        trans_record = transcribe_uploaded_audio(
            filename=file.filename,
            file_bytes=file_bytes,
            project_id=project_id,
            db=db
        )
        return trans_record
    except AudioValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "valid": False,
                "code": e.code,
                "message": e.message,
                "details": e.details
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error transcribing audio: {str(e)}"
        )

@router.get("/transcriptions/{transcription_id}", response_model=TranscriptionResponse)
def get_transcription_by_id(transcription_id: str, db: Session = Depends(get_db)):
    """Retrieves details and status of a transcription record."""
    trans = db.query(Transcription).filter(Transcription.transcription_id == transcription_id).first()
    if not trans:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription with ID '{transcription_id}' not found."
        )
    return trans

@router.patch("/transcriptions/{transcription_id}", response_model=TranscriptionResponse)
def update_transcript_text_endpoint(
    transcription_id: str,
    payload: TranscriptUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Allows human planner to edit/correct transcript text before feeding it into event extraction.
    """
    try:
        trans = update_transcription_text(transcription_id, payload.transcript, db)
        return trans
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating transcript: {str(e)}"
        )

@router.post("/transcriptions/{transcription_id}/process", response_model=VoiceProcessResponse, status_code=status.HTTP_200_OK)
@router.post("/voice/process", response_model=VoiceProcessResponse, status_code=status.HTTP_200_OK)
def process_voice_transcript_endpoint(
    transcription_id: str,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Submits a completed voice transcript into the existing text event extraction pipeline.
    Invokes EventExtractionService, preserving raw transcript text and producing structured ExtractedEvent records.
    """
    try:
        res = process_transcription_to_events(transcription_id, project_id, db)
        return res
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing transcript to events: {str(e)}"
        )
