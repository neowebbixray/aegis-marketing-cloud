"""Pydantic schemas for the Knowledge Base module: article management, categories,
search indexing, versioning.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Category ────────────────────────────────────────────────────────────────
class CategoryCreate(BaseModel):
    """Payload for POST /knowledge-base/categories."""

    name: str = Field(..., min_length=1, max_length=256)
    description: str | None = None
    parent_id: UUID | None = None
    icon: str | None = Field(None, max_length=64)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    """Payload for PATCH /knowledge-base/categories/{id}."""

    name: str | None = Field(None, min_length=1, max_length=256)
    description: str | None = None
    parent_id: UUID | None = None
    icon: str | None = Field(None, max_length=64)
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    """Knowledge base category representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    description: str | None = None
    parent_id: UUID | None = None
    icon: str | None = None
    sort_order: int
    article_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Article ─────────────────────────────────────────────────────────────────
class ArticleCreate(BaseModel):
    """Payload for POST /knowledge-base/articles."""

    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1)
    category_id: UUID | None = None
    tags: list[str] | None = None
    status: str = Field(default="draft", max_length=32)  # draft, published, archived
    is_internal: bool = False
    author_id: UUID | None = None
    seo_meta: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ArticleUpdate(BaseModel):
    """Payload for PATCH /knowledge-base/articles/{id}."""

    title: str | None = Field(None, min_length=1, max_length=512)
    content: str | None = None
    category_id: UUID | None = None
    tags: list[str] | None = None
    status: str | None = Field(None, max_length=32)
    is_internal: bool | None = None
    seo_meta: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class ArticleResponse(BaseModel):
    """Knowledge base article representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    title: str
    slug: str
    content: str
    category_id: UUID | None = None
    category_name: str | None = None
    tags: list[str] | None = None
    status: str
    is_internal: bool
    version: int
    author_id: UUID | None = None
    view_count: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    seo_meta: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ArticleVersionResponse(BaseModel):
    """Article version snapshot."""

    id: UUID
    article_id: UUID
    version: int
    title: str
    content: str
    author_id: UUID
    change_summary: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Search ──────────────────────────────────────────────────────────────────
class SearchResultResponse(BaseModel):
    """Knowledge base search result."""

    article_id: UUID
    title: str
    slug: str
    excerpt: str
    category_name: str | None = None
    tags: list[str] | None = None
    relevance_score: float = 0.0
    updated_at: datetime

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    """Knowledge base search response."""

    results: list[SearchResultResponse]
    total: int
    query: str
    suggestion: str | None = None
