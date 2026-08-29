import hashlib

def calculate_sha256(content: bytes) -> str:
    """Calculates deterministic SHA-256 hex string from raw file bytes."""
    if not isinstance(content, bytes):
        raise TypeError("Content must be bytes to calculate SHA-256 hash.")
    return hashlib.sha256(content).hexdigest()
