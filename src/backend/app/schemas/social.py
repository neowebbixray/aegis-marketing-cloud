"""
Pydantic schemas for the Social module: post scheduling, platform publishing,
engagement metrics, social listening.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Post ────────────────────────────────────────────────────────────────────
class PostCreate(BaseModel):
    """Payload for POST /social/posts."""

    platform: str = Field(..., pattern=r"^(facebook|twitter|linkedin|instagram|tiktok|youtube|pinterest)$")
    content: str = Field(..., min_length=1, max_length=5000)
    media_urls: Optional[list[str]] = None
    scheduled_at: Optional[datetime] = None
    timezone: str = Field(default="UTC", max_length=64)
    tags: Optional[list[str]] = None
    campaign_id: Optional[UUID] = None
    metadata: Optional[dict[str, Any]] = None


class PostUpdate(BaseModel):
    """Payload for PATCH /social/posts/{id}."""

    content: Optional[str] = Field(None, min_length=1, max_length=5000)
    media_urls: Optional[list[str]] = None
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = Field(None, pattern=r"^(draft|scheduled|published|cancelled)$")
    tags: Optional[list[str]] = None
    metadata: Optional[dict[str, Any]] = None


class PostResponse(BaseModel):
    """Social post representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    platform: str
    content: str
    media_urls: Optional[list[str]] = None
    status: str  # draft, scheduled, publishing, published, failed, cancelled
    scheduled_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    post_url: Optional[str] = None
    platform_post_id: Optional[str] = None
    tags: Optional[list[str]] = None
    campaign_id: Optional[UUID] = None
    metadata: Optional[dict[str, Any]] = None
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
    engagement_rate: Optional[float] = None
    followers_count: Optional[int] = None
    followers_growth: Optional[float] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    top_posts: Optional[list[dict[str, Any]]] = None


# ── Mentions / Social Listening ─────────────────────────────────────────────
class MentionResponse(BaseModel):
    """Social mention / listening entry."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    platform: str
    mention_type: str  # mention, direct_message, comment, review
    content: str
    author_handle: Optional[str] = None
    author_name: Optional[str] = None
    author_avatar: Optional[str] = None
    source_url: Optional[str] = None
    sentiment: Optional[str] = Field(None, pattern=r"^(positive|neutral|negative)$")
    relevance_score: Optional[float] = Field(None, ge=0, le=1)
    is_flagged: bool = False
    metadata: Optional[dict[str, Any]] = None
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
    tags: Optional[list[str]] = None
    campaign_name: Optional[str] = None

    model_config = {"from_attributes": True}
