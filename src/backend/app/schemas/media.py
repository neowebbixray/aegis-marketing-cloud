"""
Pydantic schemas for the Media module: assets, upload metadata, thumbnails.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Asset ─────────────────────────────────────────────────────────────────────

class AssetResponse(BaseModel):
    """Asset representation returned by the API."""

    id: UUID
    tenant_id: UUID
    user_id: Optional[UUID] = None
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_path: str
    storage_backend: str
    category: Optional[str] = None
    alt_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration_seconds: Optional[int] = None
    metadata: Optional[dict[str, Any]] = None
    is_public: bool = False
    checksum: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AssetUploadMetadata(BaseModel):
    """Metadata that can be supplied during asset upload."""

    category: Optional[str] = Field(None, max_length=50)
    alt_text: Optional[str] = Field(None, max_length=1000)
    is_public: bool = False
    metadata: Optional[dict[str, Any]] = None


class AssetUpdate(BaseModel):
    """Payload for PATCH /media/{id}. All fields optional."""

    category: Optional[str] = Field(None, max_length=50)
    alt_text: Optional[str] = Field(None, max_length=1000)
    is_public: Optional[bool] = None
    metadata: Optional[dict[str, Any]] = None


# ── Batch ─────────────────────────────────────────────────────────────────────

class BatchDeleteRequest(BaseModel):
    """Payload for DELETE /media/batch."""

    asset_ids: list[UUID] = Field(..., min_length=1, max_length=100)


class BatchDeleteResponse(BaseModel):
    """Response for batch delete."""

    deleted_count: int
    asset_ids: list[UUID]


# ── Thumbnail ─────────────────────────────────────────────────────────────────

class ThumbnailParams(BaseModel):
    """Query parameters for thumbnail generation."""

    width: int = Field(default=200, ge=16, le=4096)
    height: int = Field(default=200, ge=16, le=4096)


# ── Download URL ──────────────────────────────────────────────────────────────

class DownloadUrlResponse(BaseModel):
    """Response containing a download URL."""

    url: str
    expires_in: int
    filename: str
    mime_type: str
