"""
Pydantic schemas for the Knowledge Base module: document management, Qdrant
vector search, and indexing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Document ─────────────────────────────────────────────────────────────────
class DocumentCreate(BaseModel):
    """Payload for POST /knowledge/documents."""

    title: str = Field(..., min_length=1, max_length=512)
    content: str = Field(..., min_length=1)
    doc_type: str = Field(default="text", max_length=50)
    source: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class DocumentUpdate(BaseModel):
    """Payload for PATCH /knowledge/documents/{id}."""

    title: str | None = Field(None, min_length=1, max_length=512)
    content: str | None = None
    doc_type: str | None = Field(None, max_length=50)
    source: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=100)
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class DocumentResponse(BaseModel):
    """Knowledge document representation."""

    id: UUID
    tenant_id: UUID
    title: str
    content: str
    doc_type: str
    source: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None
    embedding_id: str | None = None
    chunk_count: int | None = None
    is_indexed: bool = False
    version: int = 1
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentUploadResponse(BaseModel):
    """Response after uploading and indexing a document."""

    document: DocumentResponse
    chunks_indexed: int = 0
    message: str = "Document uploaded and indexed successfully"


# ── Search ───────────────────────────────────────────────────────────────────
class SearchQuery(BaseModel):
    """Payload for POST /knowledge/search."""

    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=10, ge=1, le=100)
    category: str | None = Field(None, max_length=100)
    doc_type: str | None = Field(None, max_length=50)
    tags: list[str] | None = None
    threshold: float | None = Field(None, ge=0.0, le=1.0)


class SearchResult(BaseModel):
    """A single search result from Qdrant."""

    document_id: UUID
    title: str
    content: str
    score: float
    chunk_index: int | None = None
    doc_type: str | None = None
    source: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class SearchResponse(BaseModel):
    """Search response envelope."""

    results: list[SearchResult]
    total: int
    query: str


# ── Collection Stats ─────────────────────────────────────────────────────────
class CollectionStatsResponse(BaseModel):
    """Qdrant collection statistics."""

    tenant_id: UUID
    document_count: int = 0
    chunk_count: int = 0
    avg_chunk_size: int = 0
    collection_exists: bool = False


# ── Reindex ──────────────────────────────────────────────────────────────────
class ReindexResponse(BaseModel):
    """Response from a re-index operation."""

    total_documents: int = 0
    indexed: int = 0
    failed: int = 0
    errors: list[str] = []
    message: str = "Re-index complete"
