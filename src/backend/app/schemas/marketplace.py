"""Pydantic schemas for the Marketplace module: plugin/extension listings,
installation management, billing integration, review system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Listings ────────────────────────────────────────────────────────────────
class ListingResponse(BaseModel):
    """Marketplace listing representation."""

    id: UUID
    name: str
    slug: str
    short_description: str
    description: str | None = None
    category: str  # integration, plugin, template, theme, workflow
    publisher: str
    publisher_website: str | None = None
    version: str
    icon_url: str | None = None
    screenshots: list[str] | None = None
    pricing_model: str  # free, one_time, subscription, usage_based
    price: float | None = None
    currency: str = "USD"
    is_verified: bool = False
    is_featured: bool = False
    rating_avg: float | None = Field(None, ge=0, le=5)
    rating_count: int = 0
    total_installs: int = 0
    documentation_url: str | None = None
    support_url: str | None = None
    permissions_required: list[str] | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ListingDetailResponse(BaseModel):
    """Detailed marketplace listing with full description and reviews."""

    listing: ListingResponse
    recent_reviews: list[dict[str, Any]] | None = None
    changelog: list[dict[str, Any]] | None = None
    compatible_versions: list[str] | None = None
    dependencies: list[str] | None = None


# ── Installation ────────────────────────────────────────────────────────────
class InstallationResponse(BaseModel):
    """Plugin/extension installation representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    listing_id: UUID
    listing_name: str | None = None
    version_installed: str
    status: str  # installing, active, inactive, error, uninstalling
    config: dict[str, Any] | None = None
    installed_by: UUID | None = None
    last_used_at: datetime | None = None
    error_message: str | None = None
    installed_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Reviews ─────────────────────────────────────────────────────────────────
class ReviewCreate(BaseModel):
    """Payload for POST /marketplace/reviews."""

    listing_id: UUID
    rating: int = Field(..., ge=1, le=5)
    title: str | None = Field(None, max_length=256)
    content: str | None = Field(None, max_length=5000)
    pros: list[str] | None = None
    cons: list[str] | None = None


class ReviewResponse(BaseModel):
    """Marketplace review representation."""

    id: UUID
    listing_id: UUID
    user_id: UUID
    user_name: str | None = None
    user_avatar: str | None = None
    rating: int
    title: str | None = None
    content: str | None = None
    pros: list[str] | None = None
    cons: list[str] | None = None
    is_verified_purchase: bool = False
    is_flagged: bool = False
    helpful_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
