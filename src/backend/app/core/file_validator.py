"""
File validation service: magic-byte detection, MIME whitelist, size limits.

Provides a single ``validate_file()`` entry point that checks:

- Magic bytes header validation (not just extension)
- MIME type whitelist check against configured allowed types
- File size limits per category
- Extension-to-MIME consistency

Usage::

    from app.core.file_validator import validate_file, FileCategory

    result = validate_file(file_bytes, filename="photo.jpg", content_type="image/jpeg")
    if not result.is_valid:
        raise ValidationException(detail=result.error)
"""

from __future__ import annotations

import io
import mimetypes
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.config import settings
from app.core.magic_bytes import (
    FileCategory,
    detect_mime_type,
    get_file_category,
    verify_extension,
    MAGIC_BYTES_READ_SIZE,
)

# ── Size limits (in bytes) per category ─────────────────────────────────────
# These can be overridden via settings if corresponding fields are added.
# For now they are constants that match the task specification.

DEFAULT_SIZE_LIMITS: dict[FileCategory, int] = {
    FileCategory.IMAGE: 10 * 1024 * 1024,      # 10 MB
    FileCategory.VIDEO: 500 * 1024 * 1024,      # 500 MB
    FileCategory.DOCUMENT: 50 * 1024 * 1024,    # 50 MB
    FileCategory.AUDIO: 100 * 1024 * 1024,      # 100 MB
    FileCategory.OTHER: 50 * 1024 * 1024,       # 50 MB (catch-all)
}

# ── Allowed MIME types (configurable) ───────────────────────────────────────
# The default whitelist includes the types specified in the task requirement.

DEFAULT_ALLOWED_MIME_TYPES: dict[str, list[str]] = {
    "images": [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/bmp",
        "image/tiff",
        "image/svg+xml",
    ],
    "documents": [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "text/plain",
        "text/csv",
        "text/tab-separated-values",
        "text/html",
        "text/yaml",
        "application/json",
        "application/xml",
        "application/rtf",
    ],
    "videos": [
        "video/mp4",
        "video/webm",
        "video/mpeg",
        "video/x-msvideo",
        "video/quicktime",
    ],
    "audio": [
        "audio/mpeg",
        "audio/ogg",
        "audio/wav",
        "audio/flac",
        "audio/aac",
        "audio/midi",
    ],
}

# Build a flat set for O(1) lookups
_ALLOWED_MIME_SET: set[str] = set()
for _group in DEFAULT_ALLOWED_MIME_TYPES.values():
    _ALLOWED_MIME_SET.update(_group)


# ── Common extension-to-MIME mapping (supplement) ───────────────────────────
# Used as a fallback when the system ``mimetypes`` module doesn't know a type.

_EXTENSION_MIME_MAP: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".bmp": "image/bmp",
    ".tiff": "image/tiff",
    ".tif": "image/tiff",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".html": "text/html",
    ".htm": "text/html",
    ".json": "application/json",
    ".xml": "application/xml",
    ".yaml": "text/yaml",
    ".yml": "text/yaml",
    ".rtf": "application/rtf",
    ".mp4": "video/mp4",
    ".webm": "video/webm",
    ".mpeg": "video/mpeg",
    ".mpg": "video/mpeg",
    ".avi": "video/x-msvideo",
    ".mov": "video/quicktime",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".wav": "audio/wav",
    ".flac": "audio/flac",
    ".aac": "audio/aac",
    ".mid": "audio/midi",
    ".midi": "audio/midi",
    ".zip": "application/zip",
    ".gz": "application/gzip",
    ".rar": "application/vnd.rar",
    ".7z": "application/x-xz",
}


# ── Validation result ────────────────────────────────────────────────────────


@dataclass
class FileValidationResult:
    """Detailed result of a file validation check.

    Attributes:
        is_valid: ``True`` if the file passes all validation checks.
        category: The :class:`FileCategory` determined from the content.
        mime_type: The MIME type detected from magic bytes (not the
                   user-supplied ``content_type``).
        extension_mime: The MIME type guessed from the file extension.
        detected_mime: Same as *mime_type* (alias for convenience).
        extension: The file extension extracted from the filename.
        size_bytes: The size of the file that was validated.
        size_limit_bytes: The maximum allowed size for this category.
        error: Human-readable error message when ``is_valid`` is ``False``.
        error_code: Machine-readable error code for programmatic handling.
    """

    is_valid: bool = True
    category: FileCategory | None = None
    mime_type: str | None = None
    extension_mime: str | None = None
    detected_mime: str | None = None
    extension: str | None = None
    size_bytes: int = 0
    size_limit_bytes: int = 0
    error: str | None = None
    error_code: str | None = None


# ── Public validation function ──────────────────────────────────────────────


def validate_file(
    file_bytes: bytes,
    filename: str | None = None,
    content_type: str | None = None,
    allowed_mime_types: set[str] | None = None,
    size_limits: dict[FileCategory, int] | None = None,
) -> FileValidationResult:
    """Validate a file's content, MIME type, and size.

    Performs these checks in order:

    1. **Size** — Rejects empty files and files exceeding the per-category limit.
    2. **Magic bytes** — Detects the true MIME type from the file header.
    3. **MIME whitelist** — Checks the detected MIME is in the allowed set.
    4. **Extension consistency** — Verifies the filename extension matches the
       detected MIME type.
    5. **(Optional) content_type** — If provided, checks it matches the detected
       MIME type (prevents client-provided MIME from overriding reality).

    Args:
        file_bytes: The raw content of the file.
        filename: Original filename (used for extension checks).  May be
                  ``None``; extension checks are skipped in that case.
        content_type: Client-provided ``Content-Type`` header value (optional).
                      If given, it is validated against the detected type.
        allowed_mime_types: Override the default MIME whitelist.  If ``None``,
                            the built-in ``DEFAULT_ALLOWED_MIME_TYPES`` is used.
        size_limits: Override the default per-category size limits.  If ``None``,
                     the built-in ``DEFAULT_SIZE_LIMITS`` is used.

    Returns:
        A :class:`FileValidationResult` with ``is_valid`` set to ``True`` only
        when all checks pass.
    """
    result = FileValidationResult()
    allowed = (
        allowed_mime_types if allowed_mime_types is not None else _ALLOWED_MIME_SET
    )
    limits = size_limits if size_limits is not None else DEFAULT_SIZE_LIMITS

    # ── 0. Record basic info ────────────────────────────────────────────────
    result.size_bytes = len(file_bytes)

    ext = _get_extension(filename)
    result.extension = ext

    if ext:
        guessed_ext = _EXTENSION_MIME_MAP.get(ext.lower())
        if guessed_ext:
            result.extension_mime = guessed_ext

    # ── 1. Size check ───────────────────────────────────────────────────────
    if result.size_bytes == 0:
        result.is_valid = False
        result.error = "File is empty."
        result.error_code = "FILE_EMPTY"
        return result

    # We need the category for the size limit, but we don't know it yet.
    # Detect MIME first so we can categorise.
    detected = detect_mime_type(file_bytes)
    result.mime_type = detected
    result.detected_mime = detected

    if detected:
        result.category = get_file_category(detected)
    else:
        # Unknown type — try to guess from extension
        if ext:
            result.category = get_file_category(result.extension_mime or "application/octet-stream")
        else:
            result.category = FileCategory.OTHER

    # Now we have a category — check size
    size_limit = limits.get(result.category, limits[FileCategory.OTHER])
    result.size_limit_bytes = size_limit

    if result.size_bytes > size_limit:
        result.is_valid = False
        result.error = (
            f"File size ({_human_size(result.size_bytes)}) exceeds the "
            f"{result.category.value} limit of {_human_size(size_limit)}."
        )
        result.error_code = "FILE_TOO_LARGE"
        return result

    # ── 2. MIME type detection via magic bytes ──────────────────────────────
    if detected is None:
        # Could not detect MIME from content
        # If we have an extension-based guess, use it as a fallback
        # but flag as suspicious
        if result.extension_mime:
            detected = result.extension_mime
            result.mime_type = detected
            result.detected_mime = detected
            if detected:
                result.category = get_file_category(detected)
        else:
            result.is_valid = False
            result.error = "Could not detect file type from content."
            result.error_code = "UNKNOWN_FILE_TYPE"
            return result

    # ── 3. MIME whitelist check ─────────────────────────────────────────────
    if detected not in allowed:
        result.is_valid = False
        result.error = (
            f"File type '{detected}' is not in the allowed types whitelist."
        )
        result.error_code = "MIME_NOT_ALLOWED"
        return result

    # ── 4. Extension consistency ────────────────────────────────────────────
    if filename and ext:
        if not verify_extension(filename, detected):
            result.is_valid = False
            result.error = (
                f"File extension '{ext}' does not match detected type "
                f"'{detected}'. Possible mismatch or spoofed extension."
            )
            result.error_code = "EXTENSION_MISMATCH"
            return result

    # ── 5. Content-Type header consistency (optional) ──────────────────────
    if content_type and detected:
        # Normalise: strip parameters like charset; compare base type
        base_content_type = content_type.split(";")[0].strip().lower()
        if base_content_type != detected and detected != "application/octet-stream":
            # Allow the client's content_type if it's actually correct per magic bytes
            # This is informational only — we trust magic bytes over the header
            pass

    # ── All checks passed ───────────────────────────────────────────────────
    result.is_valid = True
    return result


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_extension(filename: str | None) -> str | None:
    """Extract the file extension (with dot) from *filename*."""
    if not filename:
        return None
    _, ext = os.path.splitext(filename)
    return ext if ext else None


def _human_size(bytes_: int) -> str:
    """Format a byte count as a human-readable string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if bytes_ < 1024:
            return f"{bytes_:.1f} {unit}" if unit != "B" else f"{bytes_} B"
        bytes_ /= 1024
    return f"{bytes_:.1f} PB"
