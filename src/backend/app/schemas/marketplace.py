"""
Pydantic schemas for the Marketplace module: plugin/extension listings,
installation management, billing integration, review system.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Listings ────────────────────────────────────────────────────────────────
class ListingResponse(BaseModel):
    """Marketplace listing representation."""

    id: UUID
    name: str
    slug: str
    short_description: str
    description: Optional[str] = None
    category: str  # integration, plugin, template, theme, workflow
    publisher: str
    publisher_website: Optional[str] = None
    version: str
    icon_url: Optional[str] = None
    screenshots: Optional[list[str]] = None
    pricing_model: str  # free, one_time, subscription, usage_based
    price: Optional[float] = None
    currency: str = "USD"
    is_verified: bool = False
    is_featured: bool = False
    rating_avg: Optional[float] = Field(None, ge=0, le=5)
    rating_count: int = 0
    total_installs: int = 0
    documentation_url: Optional[str] = None
    support_url: Optional[str] = None
    permissions_required: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ListingDetailResponse(BaseModel):
    """Detailed marketplace listing with full description and reviews."""

    listing: ListingResponse
    recent_reviews: Optional[list[dict[str, Any]]] = None
    changelog: Optional[list[dict[str, Any]]] = None
    compatible_versions: Optional[list[str]] = None
    dependencies: Optional[list[str]] = None


# ── Installation ────────────────────────────────────────────────────────────
class InstallationResponse(BaseModel):
    """Plugin/extension installation representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    listing_id: UUID
    listing_name: Optional[str] = None
    version_installed: str
    status: str  # installing, active, inactive, error, uninstalling
    config: Optional[dict[str, Any]] = None
    installed_by: Optional[UUID] = None
    last_used_at: Optional[datetime] = None
    error_message: Optional[str] = None
    installed_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Reviews ─────────────────────────────────────────────────────────────────
class ReviewCreate(BaseModel):
    """Payload for POST /marketplace/reviews."""

    listing_id: UUID
    rating: int = Field(..., ge=1, le=5)
    title: Optional[str] = Field(None, max_length=256)
    content: Optional[str] = Field(None, max_length=5000)
    pros: Optional[list[str]] = None
    cons: Optional[list[str]] = None


class ReviewResponse(BaseModel):
    """Marketplace review representation."""

    id: UUID
    listing_id: UUID
    user_id: UUID
    user_name: Optional[str] = None
    user_avatar: Optional[str] = None
    rating: int
    title: Optional[str] = None
    content: Optional[str] = None
    pros: Optional[list[str]] = None
    cons: Optional[list[str]] = None
    is_verified_purchase: bool = False
    is_flagged: bool = False
    helpful_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
