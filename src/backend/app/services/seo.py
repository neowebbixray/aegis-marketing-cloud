"""
SEO service: keyword tracking, rank tracking, site audit, backlink analysis.

All operations are tenant-scoped. Uses the ``SeoKeyword`` SQLAlchemy model
for persisting keyword data.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional
from uuid import UUID

from fastapi import BackgroundTasks
from sqlalchemy import Select, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.core.exceptions import NotFoundException, ValidationException
from app.models.marketing import Campaign
from app.models.seo import SeoKeyword
from app.services.base import BaseService

logger = logging.getLogger("amc.services.seo")


class KeywordService(BaseService):
    """Track and manage SEO keywords with ranking positions."""

    model = SeoKeyword

    async def track_keyword(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        keyword: str,
        target_url: str | None = None,
        search_engine: str = "google",
        location: str | None = None,
        language: str = "en",
        tags: list[str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Register a new keyword for tracking.

        Persists the keyword to the ``seo_keywords`` table and returns the
        created record as a dictionary.
        """
        obj = await self.create(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            keyword=keyword,
            target_url=target_url,
            search_engine=search_engine,
            location=location,
            language=language,
            tags=tags or [],
        )

        logger.info(
            "Tracking keyword '%s' for tenant %s (id=%s)",
            keyword, tenant_id, obj.id,
        )

        return self._keyword_to_dict(obj)

    async def list_keywords(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
        search: str | None = None,
        search_engine: str | None = None,
        sort_by: str = "keyword",
        sort_desc: bool = False,
    ) -> tuple[list[dict[str, Any]], int]:
        """List tracked keywords with current ranking data.

        Returns paginated list of keyword records and total count.
        Supports filtering by keyword text (substring match) and search engine.
        """
        filters: list[ColumnElement] = [
            SeoKeyword.workspace_id == workspace_id,
        ]

        if search:
            filters.append(SeoKeyword.keyword.ilike(f"%{search}%"))
        if search_engine:
            filters.append(SeoKeyword.search_engine == search_engine)

        # Build ordering column
        sort_map: dict[str, Any] = {
            "keyword": SeoKeyword.keyword,
            "current_rank": SeoKeyword.current_rank,
            "previous_rank": SeoKeyword.previous_rank,
            "search_volume": SeoKeyword.search_volume,
            "difficulty_score": SeoKeyword.difficulty_score,
            "last_checked_at": SeoKeyword.last_checked_at,
            "created_at": SeoKeyword.created_at,
        }
        order_col = sort_map.get(sort_by, SeoKeyword.keyword)
        order_by: ColumnElement = desc(order_col) if sort_desc else order_col

        items, total = await self.list(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            filters=filters,
            order_by=order_by,
        )

        return [self._keyword_to_dict(k) for k in items], total

    async def get_keyword(
        self,
        keyword_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Fetch a single keyword record by its primary key.

        Raises ``NotFoundException`` if the keyword does not exist or is not
        scoped to the given tenant.
        """
        obj = await self.get(id=keyword_id, tenant_id=tenant_id)
        return self._keyword_to_dict(obj)

    async def get_keyword_rankings(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        keyword_ids: list[UUID] | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Fetch current rankings for one or more keywords.

        If *keyword_ids* is ``None``, returns rankings for the most recently
        checked keywords in the workspace (up to *limit*).
        """
        stmt = select(SeoKeyword).where(
            SeoKeyword.tenant_id == tenant_id,
            SeoKeyword.workspace_id == workspace_id,
        )

        if keyword_ids:
            stmt = stmt.where(SeoKeyword.id.in_(keyword_ids))

        stmt = stmt.order_by(desc(SeoKeyword.last_checked_at)).limit(limit)

        result = await self.db.execute(stmt)
        rows = list(result.scalars().all())
        return [self._keyword_to_dict(r) for r in rows]

    # ── helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _keyword_to_dict(obj: SeoKeyword) -> dict[str, Any]:
        """Convert a ``SeoKeyword`` ORM instance to a plain dict."""
        return {
            "id": str(obj.id),
            "tenant_id": str(obj.tenant_id),
            "workspace_id": str(obj.workspace_id),
            "keyword": obj.keyword,
            "target_url": obj.target_url,
            "search_engine": obj.search_engine,
            "location": obj.location,
            "language": obj.language,
            "tags": obj.tags or [],
            "current_rank": obj.current_rank,
            "previous_rank": obj.previous_rank,
            "search_volume": obj.search_volume,
            "difficulty_score": obj.difficulty_score,
            "last_checked_at": (
                obj.last_checked_at.isoformat() if obj.last_checked_at else None
            ),
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "updated_at": obj.updated_at.isoformat() if obj.updated_at else None,
        }


class SiteAuditService(BaseService):
    """Run and manage SEO site audits."""

    model = Campaign

    async def run_audit(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        url: str,
        name: str | None = None,
        depth: int = 3,
        include_subdomains: bool = False,
        settings: dict[str, Any] | None = None,
        background_tasks: BackgroundTasks | None = None,
    ) -> dict[str, Any]:
        """Initiate a site audit for the given URL.

        Creates an audit record and dispatches a background task to
        crawl the site and collect SEO metrics.

        When *background_tasks* is provided (e.g. from a FastAPI route), a
        simulated crawl coroutine is enqueued via ``BackgroundTasks``.
        """
        audit_id = None  # placeholder — will come from a persisted model

        audit_record = {
            "url": url,
            "name": name or url,
            "depth": depth,
            "include_subdomains": include_subdomains,
            "settings": settings or {},
            "status": "pending",
            "tenant_id": str(tenant_id),
            "workspace_id": str(workspace_id),
        }
        logger.info(
            "Initiating site audit for %s (depth=%d, workspace=%s)",
            url, depth, workspace_id,
        )

        # Dispatch background crawl simulation if a task queue is provided
        if background_tasks is not None:
            background_tasks.add_task(
                self._simulate_crawl,
                audit_id=audit_id,
                url=url,
                depth=depth,
                workspace_id=workspace_id,
            )
            logger.debug(
                "Dispatched simulated crawl for audit %s (url=%s)",
                audit_id, url,
            )
        else:
            logger.debug(
                "No background_tasks provided — crawl simulation skipped for %s", url,
            )

        return audit_record

    async def _simulate_crawl(
        self,
        audit_id: UUID | None,
        url: str,
        depth: int,
        workspace_id: UUID,
    ) -> None:
        """Simulated crawl step (placeholder for real crawler integration).

        In production this would invoke a Celery task, an external crawler
        API, or a subprocess running a headless browser.
        """
        logger.info(
            "[SIMULATED CRAWL] audit=%s url=%s depth=%d workspace=%s — starting",
            audit_id, url, depth, workspace_id,
        )
        await asyncio.sleep(2)  # pretend we're doing work
        logger.info(
            "[SIMULATED CRAWL] audit=%s url=%s — complete",
            audit_id, url,
        )

    async def list_audits(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """List site audits for the workspace."""
        items: list[dict[str, Any]] = []
        total = 0
        return items, total

    async def get_audit(self, audit_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """Fetch a single site audit by ID."""
        # Stub: queries site_audits table
        raise NotFoundException(detail="Site audit not found")


class BacklinkService(BaseService):
    """Analyse and monitor backlink profiles."""

    model = Campaign

    async def list_backlinks(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        target_url: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """List backlinks pointing to workspace URLs."""
        items: list[dict[str, Any]] = []
        total = 0
        logger.debug("Listing backlinks for workspace %s", workspace_id)
        return items, total

    async def get_backlink_summary(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        target_url: str | None = None,
    ) -> dict[str, Any]:
        """Get aggregated backlink statistics.

        Returns total count, referring domains, dofollow/nofollow breakdown,
        and top referring domains.
        """
        return {
            "total_backlinks": 0,
            "referring_domains": 0,
            "dofollow_count": 0,
            "nofollow_count": 0,
            "domain_authority_avg": None,
            "top_domains": [],
        }
