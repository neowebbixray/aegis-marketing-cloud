"""
Pydantic schemas for the SEO module: keyword tracking, rank tracking, site audit, backlink analysis.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Keyword ─────────────────────────────────────────────────────────────────
class KeywordCreate(BaseModel):
    """Payload for POST /seo/keywords."""

    keyword: str = Field(..., min_length=1, max_length=512)
    target_url: Optional[str] = Field(None, max_length=2048)
    search_engine: str = Field(default="google", max_length=32)
    location: Optional[str] = Field(None, max_length=128)
    language: str = Field(default="en", max_length=16)
    tags: Optional[list[str]] = None
    custom_fields: Optional[dict[str, Any]] = None


class KeywordUpdate(BaseModel):
    """Payload for PATCH /seo/keywords/{id}."""

    keyword: Optional[str] = Field(None, min_length=1, max_length=512)
    target_url: Optional[str] = Field(None, max_length=2048)
    tags: Optional[list[str]] = None
    custom_fields: Optional[dict[str, Any]] = None


class KeywordResponse(BaseModel):
    """Keyword representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    keyword: str
    target_url: Optional[str] = None
    search_engine: str
    location: Optional[str] = None
    language: str
    current_rank: Optional[int] = None
    previous_rank: Optional[int] = None
    search_volume: Optional[int] = None
    difficulty: Optional[float] = None
    tags: Optional[list[str]] = None
    custom_fields: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Ranking ─────────────────────────────────────────────────────────────────
class RankingHistoryResponse(BaseModel):
    """Ranking history entry representation."""

    id: UUID
    keyword_id: UUID
    rank: int
    url: Optional[str] = None
    search_engine: str
    location: Optional[str] = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


# ── Site Audit ──────────────────────────────────────────────────────────────
class SiteAuditCreate(BaseModel):
    """Payload for POST /seo/audit."""

    url: str = Field(..., max_length=2048)
    name: Optional[str] = Field(None, max_length=256)
    depth: int = Field(default=3, ge=1, le=10)
    include_subdomains: bool = False
    settings: Optional[dict[str, Any]] = None


class SiteAuditResponse(BaseModel):
    """Site audit representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    url: str
    name: Optional[str] = None
    status: str  # pending, running, completed, failed
    progress: int = 0
    total_pages: Optional[int] = None
    issues_found: Optional[int] = None
    score: Optional[float] = None
    report_data: Optional[dict[str, Any]] = None
    settings: Optional[dict[str, Any]] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Backlink ────────────────────────────────────────────────────────────────
class BacklinkResponse(BaseModel):
    """Backlink representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    source_url: str
    target_url: str
    domain_authority: Optional[float] = None
    page_authority: Optional[float] = None
    is_follow: bool = True
    is_spam: Optional[bool] = None
    anchor_text: Optional[str] = None
    first_seen_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BacklinkSummaryResponse(BaseModel):
    """Aggregated backlink statistics."""

    total_backlinks: int
    referring_domains: int
    dofollow_count: int
    nofollow_count: int
    domain_authority_avg: Optional[float] = None
    top_domains: list[dict[str, Any]] = []
