"""
Pydantic schemas for the Knowledge Base module: article management, categories,
search indexing, versioning.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Category ────────────────────────────────────────────────────────────────
class CategoryCreate(BaseModel):
    """Payload for POST /knowledge-base/categories."""

    name: str = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    icon: Optional[str] = Field(None, max_length=64)
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    """Payload for PATCH /knowledge-base/categories/{id}."""

    name: Optional[str] = Field(None, min_length=1, max_length=256)
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    icon: Optional[str] = Field(None, max_length=64)
    sort_order: Optional[int] = None


class CategoryResponse(BaseModel):
    """Knowledge base category representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    name: str
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    icon: Optional[str] = None
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
    category_id: Optional[UUID] = None
    tags: Optional[list[str]] = None
    status: str = Field(default="draft", max_length=32)  # draft, published, archived
    is_internal: bool = False
    author_id: Optional[UUID] = None
    seo_meta: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None


class ArticleUpdate(BaseModel):
    """Payload for PATCH /knowledge-base/articles/{id}."""

    title: Optional[str] = Field(None, min_length=1, max_length=512)
    content: Optional[str] = None
    category_id: Optional[UUID] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = Field(None, max_length=32)
    is_internal: Optional[bool] = None
    seo_meta: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None


class ArticleResponse(BaseModel):
    """Knowledge base article representation."""

    id: UUID
    tenant_id: UUID
    workspace_id: UUID
    title: str
    slug: str
    content: str
    category_id: Optional[UUID] = None
    category_name: Optional[str] = None
    tags: Optional[list[str]] = None
    status: str
    is_internal: bool
    version: int
    author_id: Optional[UUID] = None
    view_count: int = 0
    helpful_count: int = 0
    not_helpful_count: int = 0
    seo_meta: Optional[dict[str, Any]] = None
    metadata: Optional[dict[str, Any]] = None
    published_at: Optional[datetime] = None
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
    change_summary: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Search ──────────────────────────────────────────────────────────────────
class SearchResultResponse(BaseModel):
    """Knowledge base search result."""

    article_id: UUID
    title: str
    slug: str
    excerpt: str
    category_name: Optional[str] = None
    tags: Optional[list[str]] = None
    relevance_score: float = 0.0
    updated_at: datetime

    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    """Knowledge base search response."""

    results: list[SearchResultResponse]
    total: int
    query: str
    suggestion: Optional[str] = None
