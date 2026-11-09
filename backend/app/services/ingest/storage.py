"""Document file storage manager with SHA-256 deduplication hashing."""

import hashlib
import os
import uuid
from pathlib import Path

from app.core.config import settings


def compute_file_hash(data: bytes) -> str:
    """Compute SHA-256 checksum of raw file bytes."""
    return hashlib.sha256(data).hexdigest()


def save_uploaded_file(data: bytes, original_filename: str) -> tuple[str, str, int]:
    """Persist uploaded file to storage directory with sanitized UUID path.

    Args:
        data: Raw file binary content.
        original_filename: Client-supplied filename.

    Returns:
        Tuple of (relative_storage_path, file_hash, file_size).
    """
    upload_root = Path(settings.UPLOAD_DIR)
    upload_root.mkdir(parents=True, exist_ok=True)

    file_hash = compute_file_hash(data)
    file_size = len(data)

    # Sanitize extension and assign unique storage key
    _, ext = os.path.splitext(original_filename)
    safe_ext = ext[:10].lower() if ext else ""
    storage_filename = f"{uuid.uuid4().hex}{safe_ext}"
    target_path = upload_root / storage_filename

    target_path.write_bytes(data)

    # Return relative path for portability across environments
    relative_path = str(Path(settings.UPLOAD_DIR) / storage_filename)
    return relative_path, file_hash, file_size


def get_absolute_file_path(storage_path: str) -> Path:
    """Resolve storage path to absolute filesystem path."""
    return Path(storage_path).resolve()
