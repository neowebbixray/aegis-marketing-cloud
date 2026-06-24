"""Pydantic schemas for the SEO module: keyword tracking, rank tracking, site audit, backlink analysis."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Keyword ─────────────────────────────────────────────────────────────────
class KeywordCreate(BaseModel):
    """Payload for POST /seo/keywords."""

    keyword: str = Field(..., min_length=1, max_length=512)
    target_url: str | None = Field(None, max_length=2048)
    search_engine: str = Field(default="google", max_length=32)
    location: str | None = Field(None, max_length=128)
    language: str = Field(default="en", max_length=16)
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None


class KeywordUpdate(BaseModel):
    """Payload for PATCH /seo/keywords/{id}."""

    keyword: str | None = Field(None, min_length=1, max_length=512)
    target_url: str | None = Field(None, max_length=2048)
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None


class KeywordResponse(BaseModel):
    """Keyword representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    keyword: str
    target_url: str | None = None
    search_engine: str
    location: str | None = None
    language: str
    current_rank: int | None = None
    previous_rank: int | None = None
    search_volume: int | None = None
    difficulty: float | None = None
    tags: list[str] | None = None
    custom_fields: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Ranking ─────────────────────────────────────────────────────────────────
class RankingHistoryResponse(BaseModel):
    """Ranking history entry representation."""

    id: UUID
    keyword_id: UUID
    rank: int
    url: str | None = None
    search_engine: str
    location: str | None = None
    recorded_at: datetime

    model_config = {"from_attributes": True}


# ── Site Audit ──────────────────────────────────────────────────────────────
class SiteAuditCreate(BaseModel):
    """Payload for POST /seo/audit."""

    url: str = Field(..., max_length=2048)
    name: str | None = Field(None, max_length=256)
    depth: int = Field(default=3, ge=1, le=10)
    include_subdomains: bool = False
    settings: dict[str, Any] | None = None


class SiteAuditResponse(BaseModel):
    """Site audit representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    url: str
    name: str | None = None
    status: str  # pending, running, completed, failed
    progress: int = 0
    total_pages: int | None = None
    issues_found: int | None = None
    score: float | None = None
    report_data: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
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
    domain_authority: float | None = None
    page_authority: float | None = None
    is_follow: bool = True
    is_spam: bool | None = None
    anchor_text: str | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    metadata: dict[str, Any] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class BacklinkSummaryResponse(BaseModel):
    """Aggregated backlink statistics."""

    total_backlinks: int
    referring_domains: int
    dofollow_count: int
    nofollow_count: int
    domain_authority_avg: float | None = None
    top_domains: list[dict[str, Any]] = []
