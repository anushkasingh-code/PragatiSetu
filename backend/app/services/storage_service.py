import os
import uuid
from pathlib import Path
from backend.app.config import settings

def get_upload_dir() -> Path:
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    return upload_path

def save_uploaded_file(filename: str, content: bytes) -> str:
    """
    Safely stores raw uploaded bytes on disk.
    Sanitizes filename using pathlib to prevent path traversal attacks.
    Returns relative stored path string.
    """
    target_dir = get_upload_dir()
    safe_name = Path(filename).name
    if not safe_name or safe_name in (".", ".."):
        safe_name = "uploaded_report.bin"
    
    unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    full_path = target_dir / unique_filename

    with open(full_path, "wb") as f:
        f.write(content)

    return str(full_path.relative_to(Path.cwd()) if full_path.is_relative_to(Path.cwd()) else full_path)

def delete_uploaded_file(file_path: str) -> None:
    """Removes stored file if database transaction fails."""
    path = Path(file_path)
    if path.exists() and path.is_file():
        try:
            path.unlink()
        except OSError:
            pass
