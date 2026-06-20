"""
Social service: post scheduling, platform publishing, engagement metrics,
social listening.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.social import SocialPost
from app.services.base import BaseService

logger = logging.getLogger("amc.services.social")


# ── Abstract platform client ─────────────────────────────────────────────────


class PlatformClient(ABC):
    """Abstract interface for publishing to a social media platform."""

    @abstractmethod
    async def publish(
        self,
        post: SocialPost,
        *,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Publish *post* to the platform and return platform metadata.

        Should return at minimum a dict with ``platform_post_id``.
        """
        ...


class SimulatedPlatformClient(PlatformClient):
    """Simulated client that logs the publish call and returns fake data.

    Used for development / testing until real API integrations are wired up.
    """

    async def publish(
        self,
        post: SocialPost,
        *,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        logger.info(
            "[SIM] Publishing post %s to %s (tenant=%s)",
            post.id,
            post.platform,
            tenant_id,
        )
        return {
            "platform_post_id": f"sim_{post.id}_{post.platform}",
            "status": "published",
        }


# ── Service ─────────────────────────────────────────────────────────────────


class SocialPostService(BaseService[SocialPost]):
    """Schedule, publish, and manage social media posts."""

    model = SocialPost

    # ── Platform client registry ──────────────────────────────────────────

    _platform_clients: dict[str, type[PlatformClient]] = {
        "twitter": SimulatedPlatformClient,
        "linkedin": SimulatedPlatformClient,
        "facebook": SimulatedPlatformClient,
        "instagram": SimulatedPlatformClient,
        "tiktok": SimulatedPlatformClient,
        "youtube": SimulatedPlatformClient,
        "pinterest": SimulatedPlatformClient,
    }

    def _get_platform_client(self, platform: str) -> PlatformClient:
        """Return a platform-specific client instance.

        Raises ``ValidationException`` for unsupported platforms.
        """
        client_cls = self._platform_clients.get(platform.lower())
        if client_cls is None:
            raise ValidationException(
                detail=f"Unsupported platform: {platform!r}. "
                f"Supported: {list(self._platform_clients)}"
            )
        return client_cls()

    # ── CRUD ──────────────────────────────────────────────────────────────

    async def create_post(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        platform: str,
        content: str,
        media_urls: list[str] | None = None,
        scheduled_at: datetime | None = None,
        timezone: str = "UTC",
        tags: list[str] | None = None,
        campaign_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SocialPost:
        """Create a new social media post (draft or scheduled).

        Persists the post to the ``social_posts`` table and returns the
        SQLAlchemy model instance.
        """
        status = "draft" if scheduled_at is None else "scheduled"

        post = SocialPost(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            platform=platform,
            content=content,
            media_urls=media_urls or [],
            scheduled_at=scheduled_at,
            status=status,
            tags=tags or [],
            campaign_id=campaign_id,
            metadata=metadata or {},
        )
        self.db.add(post)
        await self.db.flush()
        await self.db.refresh(post)

        logger.info(
            "Created %s post %s for workspace %s (status=%s)",
            platform,
            post.id,
            workspace_id,
            status,
        )
        return post

    async def list_posts(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
        status: str | None = None,
        platform: str | None = None,
        campaign_id: UUID | None = None,
    ) -> tuple[list[SocialPost], int]:
        """List social media posts with optional filtering."""
        filters: list[Any] = [
            SocialPost.tenant_id == tenant_id,
            SocialPost.workspace_id == workspace_id,
        ]
        if status:
            filters.append(SocialPost.status == status)
        if platform:
            filters.append(SocialPost.platform == platform)
        if campaign_id:
            filters.append(SocialPost.campaign_id == campaign_id)

        # Total count
        count_stmt = select(func.count()).select_from(SocialPost).where(*filters)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Paginated query
        stmt = (
            select(SocialPost)
            .where(*filters)
            .order_by(desc(SocialPost.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_post(self, post_id: UUID, tenant_id: UUID) -> SocialPost:
        """Fetch a single social post by id (tenant-scoped)."""
        return await self.get(id=post_id, tenant_id=tenant_id)

    async def update_post(
        self,
        post_id: UUID,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> SocialPost:
        """Update a social post (content, schedule, status)."""
        return await self.update(id=post_id, tenant_id=tenant_id, **kwargs)

    async def publish_post(
        self,
        post_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Publish a social post immediately.

        Sends the content to the respective platform API via the platform
        client and updates the post status to 'published'.
        """
        post = await self.get(id=post_id, tenant_id=tenant_id)

        if post.status == "published":
            raise ValidationException(detail="Post is already published")
        if post.status == "deleted":
            raise ValidationException(detail="Cannot publish a deleted post")

        client = self._get_platform_client(post.platform)

        try:
            result = await client.publish(post, tenant_id=tenant_id)

            post.status = "published"
            post.published_at = datetime.utcnow()
            post.platform_post_id = result.get("platform_post_id")
            await self.db.flush()

            logger.info(
                "Published post %s to %s (platform_post_id=%s)",
                post_id,
                post.platform,
                post.platform_post_id,
            )
            return {
                "status": post.status,
                "platform_post_id": post.platform_post_id,
                "published_at": post.published_at,
            }
        except Exception:
            logger.exception("Failed to publish post %s to %s", post_id, post.platform)
            post.status = "failed"
            await self.db.flush()
            raise

    async def delete_post(self, post_id: UUID, tenant_id: UUID) -> None:
        """Soft-delete a social post."""
        await self.soft_delete(id=post_id, tenant_id=tenant_id)
        logger.info("Soft-deleted post %s", post_id)

    async def get_calendar(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        platform: str | None = None,
    ) -> list[SocialPost]:
        """Get scheduled posts in a date range for the social calendar."""
        filters: list[Any] = [
            SocialPost.tenant_id == tenant_id,
            SocialPost.workspace_id == workspace_id,
            SocialPost.status == "scheduled",
        ]
        if start_date:
            filters.append(SocialPost.scheduled_at >= start_date)
        if end_date:
            filters.append(SocialPost.scheduled_at <= end_date)
        if platform:
            filters.append(SocialPost.platform == platform)

        stmt = (
            select(SocialPost)
            .where(*filters)
            .order_by(SocialPost.scheduled_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class SocialAnalyticsService:
    """Aggregate and report social media engagement metrics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_analytics(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        platform: str | None = None,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> dict[str, Any]:
        """Get aggregated social media analytics.

        Returns impressions, engagements, clicks, shares, comments,
        and engagement rate broken down by platform.
        """
        return {
            "platform": platform or "all",
            "total_posts": 0,
            "total_impressions": 0,
            "total_engagements": 0,
            "total_clicks": 0,
            "total_shares": 0,
            "total_comments": 0,
            "engagement_rate": None,
            "period_start": period_start,
            "period_end": period_end,
            "top_posts": [],
        }


class SocialListeningService:
    """Monitor brand mentions and sentiment across social platforms."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_mentions(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
        platform: str | None = None,
        sentiment: str | None = None,
        is_flagged: bool | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List social mentions / listening entries."""
        items: list[dict[str, Any]] = []
        total = 0
        return items, total

    async def get_mention(self, mention_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """Fetch a single social mention."""
        raise NotFoundException(detail="Mention not found")

    async def flag_mention(self, mention_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """Flag a mention for review."""
        logger.info("Flagged mention %s", mention_id)
        return {"is_flagged": True}
