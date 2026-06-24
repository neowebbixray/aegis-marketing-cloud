"""Full-text search service using PostgreSQL tsvector + tsquery.

Provides entity-specific search methods (contacts, deals, campaigns) as
well as a unified ``global_search`` that returns results grouped by entity
type.  All queries use ``ts_rank()`` for relevance scoring and ``plainto_tsquery``
for a forgiving user-facing search syntax.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.search import SearchResultItem

logger = logging.getLogger("amc.services.search")

# ── Search rank threshold (0.0 – 1.0) ────────────────────────────────────────
MIN_RANK = 0.01

# ── SQL templates ─────────────────────────────────────────────────────────────

_SEARCH_CONTACTS_SQL = """
SELECT
    id AS entity_id,
    CONCAT_WS(' ', first_name, last_name) AS title,
    CONCAT_WS(', ',
        NULLIF(first_name || ' ' || last_name, ' '),
        NULLIF(email, ''),
        NULLIF(company, '')
    ) AS snippet,
    ts_rank(search_vector, query, 1) AS rank,
    workspace_id,
    created_at,
    updated_at
FROM contacts, plainto_tsquery('english', :query) AS query
WHERE
    search_vector @@ query
    AND workspace_id = :workspace_id
    AND deleted_at IS NULL
    AND ts_rank(search_vector, query, 1) >= :min_rank
ORDER BY rank DESC
LIMIT :limit
OFFSET :offset
"""

_COUNT_CONTACTS_SQL = """
SELECT count(*) AS total
FROM contacts, plainto_tsquery('english', :query) AS query
WHERE
    search_vector @@ query
    AND workspace_id = :workspace_id
    AND deleted_at IS NULL
"""

_SEARCH_DEALS_SQL = """
SELECT
    id AS entity_id,
    name AS title,
    CONCAT_WS(', ',
        NULLIF(name, ''),
        NULLIF(organization_label, ''),
        'value: $' || value::text
    ) AS snippet,
    ts_rank(search_vector, query, 1) AS rank,
    workspace_id,
    created_at,
    updated_at
FROM deals, plainto_tsquery('english', :query) AS query
WHERE
    search_vector @@ query
    AND workspace_id = :workspace_id
    AND deleted_at IS NULL
    AND ts_rank(search_vector, query, 1) >= :min_rank
ORDER BY rank DESC
LIMIT :limit
OFFSET :offset
"""

_COUNT_DEALS_SQL = """
SELECT count(*) AS total
FROM deals, plainto_tsquery('english', :query) AS query
WHERE
    search_vector @@ query
    AND workspace_id = :workspace_id
    AND deleted_at IS NULL
"""

_SEARCH_CAMPAIGNS_SQL = """
SELECT
    id AS entity_id,
    name AS title,
    CONCAT_WS(', ',
        NULLIF(name, ''),
        NULLIF(description, ''),
        NULLIF(campaign_type, ''),
        NULLIF(channel, '')
    ) AS snippet,
    ts_rank(search_vector, query, 1) AS rank,
    workspace_id,
    created_at,
    updated_at
FROM campaigns, plainto_tsquery('english', :query) AS query
WHERE
    search_vector @@ query
    AND workspace_id = :workspace_id
    AND deleted_at IS NULL
    AND ts_rank(search_vector, query, 1) >= :min_rank
ORDER BY rank DESC
LIMIT :limit
OFFSET :offset
"""

_COUNT_CAMPAIGNS_SQL = """
SELECT count(*) AS total
FROM campaigns, plainto_tsquery('english', :query) AS query
WHERE
    search_vector @@ query
    AND workspace_id = :workspace_id
    AND deleted_at IS NULL
"""


# ── Service ───────────────────────────────────────────────────────────────────


class SearchService:
    """Full-text search across CRM and marketing entities.

    All methods accept a **workspace_id** for tenant-scoped isolation and
    return ranked results with relevance scores.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _rows_to_items(rows: list[Any], entity_type: str) -> list[SearchResultItem]:
        """Convert raw SQL result rows to ``SearchResultItem`` instances."""
        items: list[SearchResultItem] = []
        for row in rows:
            items.append(
                SearchResultItem(
                    entity_type=entity_type,
                    entity_id=row[0],
                    title=row[1],
                    snippet=row[2],
                    rank=float(row[3]),
                    workspace_id=row[4],
                    extra={},
                ),
            )
        return items

    async def _run_search(
        self,
        search_sql: str,
        count_sql: str,
        query: str,
        workspace_id: UUID,
        skip: int,
        limit: int,
        entity_type: str,
    ) -> tuple[list[SearchResultItem], int]:
        """Execute a search query and count query, return (items, total)."""
        params = {
            "query": query,
            "workspace_id": workspace_id,
            "min_rank": MIN_RANK,
            "limit": limit,
            "offset": skip,
        }

        # Fetch results
        result = await self.db.execute(text(search_sql).bindparams(**params))
        rows = result.fetchall()
        items = self._rows_to_items(rows, entity_type)

        # Fetch total count
        count_params = {
            "query": query,
            "workspace_id": workspace_id,
        }
        count_result = await self.db.execute(text(count_sql).bindparams(**count_params))
        total = count_result.scalar_one()

        return items, total

    # ── Entity-specific search ─────────────────────────────────────────────────

    async def search_contacts(
        self,
        query: str,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SearchResultItem], int]:
        """Full-text search across contacts (name, email, company, phone, etc.)."""
        return await self._run_search(
            _SEARCH_CONTACTS_SQL,
            _COUNT_CONTACTS_SQL,
            query,
            workspace_id,
            skip,
            limit,
            "contact",
        )

    async def search_deals(
        self,
        query: str,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SearchResultItem], int]:
        """Full-text search across deals (name, organization_label)."""
        return await self._run_search(
            _SEARCH_DEALS_SQL,
            _COUNT_DEALS_SQL,
            query,
            workspace_id,
            skip,
            limit,
            "deal",
        )

    async def search_campaigns(
        self,
        query: str,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[SearchResultItem], int]:
        """Full-text search across campaigns (name, description, type, channel)."""
        return await self._run_search(
            _SEARCH_CAMPAIGNS_SQL,
            _COUNT_CAMPAIGNS_SQL,
            query,
            workspace_id,
            skip,
            limit,
            "campaign",
        )

    # ── Global search ─────────────────────────────────────────────────────────

    async def global_search(
        self,
        query: str,
        workspace_id: UUID,
        limit_per_type: int = 5,
    ) -> dict[str, Any]:
        """Unified search across contacts, deals, and campaigns.

        Returns a dict with the original query and a list of per-entity groups::

            {
                "query": str,
                "results": [
                    {
                        "entity_type": "contact",
                        "results": [...],
                        "total": int,
                    },
                    ...
                ],
                "total": int,
            }
        """
        groups: list[dict[str, Any]] = []
        grand_total = 0

        for search_fn, etype in (
            (self.search_contacts, "contact"),
            (self.search_deals, "deal"),
            (self.search_campaigns, "campaign"),
        ):
            items, total = await search_fn(
                query=query,
                workspace_id=workspace_id,
                skip=0,
                limit=limit_per_type,
            )
            if items:
                groups.append(
                    {
                        "entity_type": etype,
                        "results": [item.model_dump() for item in items],
                        "total": total,
                    },
                )
                grand_total += total

        return {
            "query": query,
            "results": groups,
            "total": grand_total,
        }

    # ── Re-index ──────────────────────────────────────────────────────────────

    async def reindex_all(self) -> dict[str, int]:
        """Rebuild the search_vector column for all entities.

        Delegates to :func:`app.core.search_indexer.reindex_all`.
        """
        from app.core.search_indexer import reindex_all

        return await reindex_all(self.db)
