"""Pydantic schemas for the Media module: assets, upload metadata, thumbnails."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

# ── Asset ─────────────────────────────────────────────────────────────────────


class AssetResponse(BaseModel):
    """Asset representation returned by the API."""

    id: UUID
    tenant_id: UUID
    user_id: UUID | None = None
    filename: str
    original_filename: str
    mime_type: str
    size_bytes: int
    storage_path: str
    storage_backend: str
    category: str | None = None
    alt_text: str | None = None
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None
    metadata: dict[str, Any] | None = None
    is_public: bool = False
    checksum: str | None = None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None

    model_config = {"from_attributes": True}


class AssetUploadMetadata(BaseModel):
    """Metadata that can be supplied during asset upload."""

    category: str | None = Field(None, max_length=50)
    alt_text: str | None = Field(None, max_length=1000)
    is_public: bool = False
    metadata: dict[str, Any] | None = None


class AssetUpdate(BaseModel):
    """Payload for PATCH /media/{id}. All fields optional."""

    category: str | None = Field(None, max_length=50)
    alt_text: str | None = Field(None, max_length=1000)
    is_public: bool | None = None
    metadata: dict[str, Any] | None = None


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
