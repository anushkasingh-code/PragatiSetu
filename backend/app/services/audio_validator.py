import os
from pathlib import Path
from backend.app.config import settings

ALLOWED_AUDIO_EXTENSIONS = {".wav", ".mp3", ".m4a", ".webm", ".ogg", ".flac"}

class AudioValidationError(Exception):
    def __init__(self, message: str, code: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

def sanitize_audio_filename(filename: str) -> str:
    if not filename:
        return "unnamed_audio.wav"
    clean_name = os.path.basename(filename)
    clean_name = clean_name.replace("..", "").replace("/", "").replace("\\", "")
    return clean_name or "unnamed_audio.wav"

def validate_audio_file_content(filename: str, file_bytes: bytes) -> dict:
    clean_filename = sanitize_audio_filename(filename)
    ext = Path(clean_filename).suffix.lower()

    if ext not in ALLOWED_AUDIO_EXTENSIONS:
        raise AudioValidationError(
            message=f"Unsupported audio file extension '{ext}'. Allowed extensions are: {sorted(list(ALLOWED_AUDIO_EXTENSIONS))}",
            code="UNSUPPORTED_AUDIO_FORMAT",
            details={"filename": clean_filename, "extension": ext, "supported_extensions": sorted(list(ALLOWED_AUDIO_EXTENSIONS))}
        )

    file_size = len(file_bytes)
    if file_size == 0:
        raise AudioValidationError(
            message="Audio file is empty (0 bytes).",
            code="EMPTY_AUDIO_FILE",
            details={"filename": clean_filename}
        )

    max_size = settings.MAX_AUDIO_SIZE_BYTES
    if file_size > max_size:
        raise AudioValidationError(
            message=f"Audio file size ({file_size} bytes) exceeds maximum limit ({max_size} bytes / {max_size // (1024 * 1024)} MB).",
            code="AUDIO_TOO_LARGE",
            details={"filename": clean_filename, "file_size": file_size, "max_allowed_bytes": max_size}
        )

    return {
        "valid": True,
        "filename": clean_filename,
        "extension": ext,
        "file_size": file_size
    }
