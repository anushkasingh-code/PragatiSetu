from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.db.models.transcription import Transcription
from backend.app.schemas.voice import TranscriptionResponse, TranscriptUpdateRequest, VoiceProcessResponse, VoiceProcessRequest
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
            filename=file.filename or "unknown",
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
            detail=f"Speech transcription failed: {str(e)}"
        )

@router.get("/transcriptions/{transcription_id}", response_model=TranscriptionResponse)
def get_transcription_endpoint(transcription_id: str, db: Session = Depends(get_db)):
    """Retrieves an existing audio transcription record."""
    t = db.query(Transcription).filter(Transcription.transcription_id == transcription_id).first()
    if not t:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcription with ID '{transcription_id}' not found."
        )
    return t

@router.patch("/transcriptions/{transcription_id}", response_model=TranscriptionResponse)
def update_transcript_endpoint(
    transcription_id: str,
    payload: TranscriptUpdateRequest,
    db: Session = Depends(get_db)
):
    """Allows human planner to edit/correct a generated audio transcript prior to downstream processing."""
    try:
        updated = update_transcription_text(transcription_id, payload.transcript, db)
        return updated
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
def process_transcription_endpoint(
    transcription_id: str,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Submits a completed voice transcript into the existing text event extraction pipeline by path param.
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

@router.post("/voice/process", response_model=VoiceProcessResponse, status_code=status.HTTP_200_OK)
def process_voice_endpoint(
    payload: Optional[VoiceProcessRequest] = None,
    transcription_id: Optional[str] = None,
    project_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Submits a completed voice transcript via POST /voice/process accepting body payload or query parameters.
    """
    tid = (payload.transcription_id if payload and payload.transcription_id else transcription_id)
    if not tid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Field 'transcription_id' is required in request body or query parameters."
        )
    pid = (payload.project_id if payload and payload.project_id else project_id)
    try:
        res = process_transcription_to_events(tid, pid, db)
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
