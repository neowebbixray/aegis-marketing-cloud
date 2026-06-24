"""Pydantic schemas for the Social module: post scheduling, platform publishing,
engagement metrics, social listening.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Post ────────────────────────────────────────────────────────────────────
class PostCreate(BaseModel):
    """Payload for POST /social/posts."""

    platform: str = Field(
        ..., pattern=r"^(facebook|twitter|linkedin|instagram|tiktok|youtube|pinterest)$"
    )
    content: str = Field(..., min_length=1, max_length=5000)
    media_urls: list[str] | None = None
    scheduled_at: datetime | None = None
    timezone: str = Field(default="UTC", max_length=64)
    tags: list[str] | None = None
    campaign_id: UUID | None = None
    metadata: dict[str, Any] | None = None


class PostUpdate(BaseModel):
    """Payload for PATCH /social/posts/{id}."""

    content: str | None = Field(None, min_length=1, max_length=5000)
    media_urls: list[str] | None = None
    scheduled_at: datetime | None = None
    status: str | None = Field(None, pattern=r"^(draft|scheduled|published|cancelled)$")
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class PostResponse(BaseModel):
    """Social post representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    platform: str
    content: str
    media_urls: list[str] | None = None
    status: str  # draft, scheduled, publishing, published, failed, cancelled
    scheduled_at: datetime | None = None
    published_at: datetime | None = None
    post_url: str | None = None
    platform_post_id: str | None = None
    tags: list[str] | None = None
    campaign_id: UUID | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Analytics ───────────────────────────────────────────────────────────────
class SocialAnalyticsResponse(BaseModel):
    """Aggregated social media analytics."""

    platform: str
    total_posts: int = 0
    total_impressions: int = 0
    total_engagements: int = 0
    total_clicks: int = 0
    total_shares: int = 0
    total_comments: int = 0
    engagement_rate: float | None = None
    followers_count: int | None = None
    followers_growth: float | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    top_posts: list[dict[str, Any]] | None = None


# ── Mentions / Social Listening ─────────────────────────────────────────────
class MentionResponse(BaseModel):
    """Social mention / listening entry."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    platform: str
    mention_type: str  # mention, direct_message, comment, review
    content: str
    author_handle: str | None = None
    author_name: str | None = None
    author_avatar: str | None = None
    source_url: str | None = None
    sentiment: str | None = Field(None, pattern=r"^(positive|neutral|negative)$")
    relevance_score: float | None = Field(None, ge=0, le=1)
    is_flagged: bool = False
    metadata: dict[str, Any] | None = None
    mentioned_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Calendar ────────────────────────────────────────────────────────────────
class CalendarEntryResponse(BaseModel):
    """Social calendar entry."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    post_id: UUID
    platform: str
    content_preview: str
    status: str
    scheduled_at: datetime
    media_count: int = 0
    tags: list[str] | None = None
    campaign_name: str | None = None

    model_config = {"from_attributes": True}
