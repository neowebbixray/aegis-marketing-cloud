"""
Magic byte signatures database for file type detection.

Provides functions to detect MIME types from raw byte prefixes, map MIME types
to file categories, and verify that a file's extension matches its true content.
"""

from __future__ import annotations

import enum
import os
from typing import Optional


class FileCategory(str, enum.Enum):
    """Categorisation of files based on MIME type group."""

    IMAGE = "image"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    OTHER = "other"


# ── Maximum bytes to read for magic-byte detection ──────────────────────────
MAGIC_BYTES_READ_SIZE = 32  # ample for all signatures below

# ── Signature definition ────────────────────────────────────────────────────
# Each entry: bytes_prefix -> (mime_type, description)
# Prefixes are bytes objects compared against the start of the file.
# Longer prefixes are tried first (most specific match wins).

FILE_SIGNATURES: list[tuple[bytes, str, str]] = [
    # ── Images ──────────────────────────────────────────────────────────────
    (b"\xff\xd8\xff", "image/jpeg", "JPEG image"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "PNG image"),
    (b"GIF87a", "image/gif", "GIF image (87a)"),
    (b"GIF89a", "image/gif", "GIF image (89a)"),
    (b"RIFF", "image/webp", "WebP image"),  # verified by extra check below
    (b"BM", "image/bmp", "BMP image"),
    (b"II*\x00", "image/tiff", "TIFF image (little-endian)"),
    (b"MM\x00*", "image/tiff", "TIFF image (big-endian)"),
    # ── Documents ───────────────────────────────────────────────────────────
    (b"%PDF", "application/pdf", "PDF document"),
    (
        b"PK\x03\x04",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "DOCX / Office Open XML",
    ),
    # ── Vector graphics ─────────────────────────────────────────────────────
    (b"<?xml ", "image/svg+xml", "SVG (XML-based)"),  # verified by extra check
    (b"<svg", "image/svg+xml", "SVG element"),
    (b"\xef\xbb\xbf<svg", "image/svg+xml", "SVG with BOM"),
    # ── Video ────────────────────────────────────────────────────────────────
    (b"\x00\x00\x00\x18ftyp", "video/mp4", "MP4 video"),
    (b"\x00\x00\x00\x1cftyp", "video/mp4", "MP4 video (ISO)"),
    (b"\x00\x00\x00\x20ftyp", "video/mp4", "MP4 video (avc1)"),
    (b"\x00\x00\x00 ftyp", "video/mp4", "MP4 video (iso2)"),
    (b"ftyp", "video/mp4", "MP4 video (offset ftyp)"),
    (b"\x1aE\xdf\xa3", "video/webm", "WebM video (Matroska)"),
    (b"\x00\x00\x01\xba", "video/mpeg", "MPEG video"),
    (b"\x00\x00\x01\xb3", "video/mpeg", "MPEG video (sequence)"),
    # ── Audio ────────────────────────────────────────────────────────────────
    (b"ID3", "audio/mpeg", "MP3 audio (ID3 tag)"),
    (b"\xff\xfb", "audio/mpeg", "MP3 audio (MPEG 1 Layer 3)"),
    (b"\xff\xf3", "audio/mpeg", "MP3 audio (MPEG 2 Layer 3)"),
    (b"\xff\xf2", "audio/mpeg", "MP3 audio (MPEG 2.5 Layer 3)"),
    (b"OggS", "audio/ogg", "OGG audio container"),
    (b"RIFF", "audio/wav", "WAV audio"),  # disambiguated via extra check
    (b"fLaC", "audio/flac", "FLAC audio"),
    (b"MThd", "audio/midi", "MIDI audio"),
    # ── Archives / other ─────────────────────────────────────────────────────
    (b"PK\x03\x04", "application/zip", "ZIP archive"),
    (b"Rar!\x1a\x07", "application/vnd.rar", "RAR archive"),
    (b"\x1f\x8b", "application/gzip", "GZip archive"),
    (b"BZh", "application/x-bzip2", "BZip2 archive"),
    (b"\xfd7zXZ\x00", "application/x-xz", "XZ archive"),
]

# ── Whitelist mapping for disambiguation ────────────────────────────────────
# Some signatures (e.g. RIFF, PK\x03\x04, <?xml) match multiple types.
# We resolve by inspecting bytes beyond the prefix.

_RiffSubTypeMap: dict[bytes, str] = {
    b"WEBP": "image/webp",
    b"WAVE": "audio/wav",
    b"AVI ": "video/x-msvideo",
}


def _check_riff_type(data: bytes) -> str | None:
    """Inspect a RIFF header to determine the sub-type."""
    if len(data) < 12:
        return None
    sub_type = data[8:12]
    return _RiffSubTypeMap.get(sub_type)


def _check_svg_xml(data: bytes) -> str | None:
    """Verify an XML-prefixed file is actually SVG."""
    if len(data) < 64:
        return None
    lower = data[:64].lower()
    if b"<svg" in lower or b"<!doctype svg" in lower or b"<svg " in lower:
        return "image/svg+xml"
    return None


# ── Signature matchers with disambiguation ───────────────────────────────────
_EXTRA_CHECKS: dict[bytes, list[callable[[bytes], str | None]]] = {
    b"RIFF": [_check_riff_type],
    b"<?xml ": [_check_svg_xml],
}


def detect_mime_type(file_bytes: bytes) -> str | None:
    """Detect the MIME type of *file_bytes* using magic byte signatures.

    Returns ``None`` when the type cannot be determined.
    """
    if not file_bytes:
        return None

    # Sort signatures: longer prefixes first for most-specific match
    for prefix, mime, _desc in sorted(
        FILE_SIGNATURES, key=lambda x: -len(x[0])
    ):
        if file_bytes.startswith(prefix):
            # Run extra checks if available for this prefix
            extra = _EXTRA_CHECKS.get(prefix)
            if extra:
                for check_fn in extra:
                    result = check_fn(file_bytes)
                    if result is not None:
                        return result
                # Extra checks didn't resolve — continue to next signature
                continue
            return mime

    # ── Plain-text heuristics (last resort) ──────────────────────────────
    # No signature matched; check whether the content looks like text
    try:
        if b"\x00" not in file_bytes[:512]:
            decoded = file_bytes[:1024].decode("utf-8")
            if decoded.isprintable() or any(c.isalpha() for c in decoded):
                return "text/plain"
    except (UnicodeDecodeError, ValueError):
        pass

    return None


def get_file_category(mime_type: str) -> FileCategory:
    """Map a MIME type to a :class:`FileCategory`.

    Args:
        mime_type: The MIME type string to categorise.

    Returns:
        The corresponding :class:`FileCategory` enum member.
        Falls back to ``OTHER`` for unrecognised types.
    """
    major = mime_type.split("/")[0] if "/" in mime_type else ""
    mime_lower = mime_type.lower()

    if major == "image":
        return FileCategory.IMAGE
    if major == "video":
        return FileCategory.VIDEO
    if major == "audio":
        return FileCategory.AUDIO
    if major == "text":
        return FileCategory.DOCUMENT

    # Application subtypes that are documents
    doc_prefixes = (
        "pdf",
        "document",
        "spreadsheet",
        "presentation",
        "msword",
        "ms-excel",
        "ms-powerpoint",
        "opendocument",
        "rtf",
        "epub",
    )
    if any(p in mime_lower for p in doc_prefixes):
        return FileCategory.DOCUMENT

    if major == "application":
        # Common document-like application types
        app_docs: set[str] = {
            "application/pdf",
            "application/rtf",
            "application/epub+zip",
            "application/vnd.oasis.opendocument.text",
            "application/vnd.oasis.opendocument.spreadsheet",
        }
        if mime_lower in app_docs:
            return FileCategory.DOCUMENT
        return FileCategory.OTHER

    return FileCategory.OTHER


def verify_extension(filename: str, detected_mime: str) -> bool:
    """Check whether *filename*'s extension is consistent with *detected_mime*.

    Uses the standard library ``mimetypes`` module with common additions.
    Returns ``True`` if the extension matches the detected type or the detected
    type could not be identified (don't reject on unknown).

    Relaxed matching is applied for ``text/*`` subtypes (e.g. ``text/plain``
    vs. ``text/csv``) since many text-based file formats do not have distinct
    magic bytes.

    Args:
        filename: Original filename (or any string with an extension).
        detected_mime: The MIME type detected from magic bytes.

    Returns:
        ``True`` if the extension is consistent with the detected MIME type.
    """
    if not detected_mime:
        return True  # can't verify, don't reject

    import mimetypes

    _ensure_mimetypes(mimetypes)

    _, ext = os.path.splitext(filename.lower())
    if not ext:
        return True  # no extension to verify against

    guessed = mimetypes.guess_type(f"file{ext}")[0]
    if guessed is None:
        return True  # unknown extension, don't reject

    # Exact match
    if guessed == detected_mime:
        return True

    # Relaxed matching: if both are text/* subtypes, allow it
    # (e.g. .csv -> text/csv, magic -> text/plain)
    guessed_major = guessed.split("/")[0] if "/" in guessed else ""
    detected_major = detected_mime.split("/")[0] if "/" in detected_mime else ""
    if guessed_major == "text" and detected_major == "text":
        return True

    return False


def _ensure_mimetypes(mimetypes_module) -> None:
    """Register common MIME type mappings not present on all platforms."""
    types: dict[str, str] = {
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".opus": "audio/ogg",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".csv": "text/csv",
        ".tsv": "text/tab-separated-values",
        ".yaml": "text/yaml",
        ".yml": "text/yaml",
        ".json": "application/json",
        ".xml": "application/xml",
    }
    for ext, mime in types.items():
        mimetypes_module.add_type(mime, ext)
