"""Search response schemas for full-text search across entities."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SearchResultItem(BaseModel):
    """A single search result from any entity type."""

    entity_type: str = Field(
        ..., description="Type of entity: contact, deal, campaign"
    )
    entity_id: UUID = Field(..., description="UUID of the matched entity")
    title: str = Field(..., description="Display title for the result")
    snippet: Optional[str] = Field(
        None, description="Relevant text snippet from the matched fields"
    )
    rank: float = Field(..., ge=0.0, le=1.0, description="ts_rank relevance score")
    workspace_id: UUID = Field(..., description="Workspace the entity belongs to")
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Entity-specific additional fields",
    )


class SearchResults(BaseModel):
    """Paginated list of search results from a single entity type."""

    items: list[SearchResultItem]
    total: int
    page: int = 1
    per_page: int = 20
    has_more: bool = False


class GlobalSearchResultItem(BaseModel):
    """A single result in global search grouped by entity type."""

    entity_type: str
    results: list[SearchResultItem]
    total: int


class GlobalSearchResults(BaseModel):
    """Unified search results across all entity types."""

    query: str
    results: list[GlobalSearchResultItem]
    total: int
