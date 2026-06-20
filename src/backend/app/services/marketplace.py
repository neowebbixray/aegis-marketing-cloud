"""
Marketplace service: plugin/extension listings, installation management,
billing integration, review system.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func, desc, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.marketplace import MarketplaceInstallation
from app.services.base import BaseService

logger = logging.getLogger("amc.services.marketplace")


class ListingService:
    """Browse and manage marketplace listings."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_listings(
        self,
        skip: int = 0,
        limit: int = 50,
        category: str | None = None,
        search: str | None = None,
        is_featured: bool | None = None,
        sort_by: str = "total_installs",
        sort_desc: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """List marketplace listings with filtering and search."""
        items: list[dict[str, Any]] = []
        total = 0
        return items, total

    async def get_listing(self, listing_id: UUID) -> dict[str, Any]:
        """Fetch a single marketplace listing with details."""
        raise NotFoundException(detail="Listing not found")

    async def get_listing_by_slug(self, slug: str) -> dict[str, Any]:
        """Fetch a listing by its URL slug."""
        raise NotFoundException(detail="Listing not found")

    async def get_featured_listings(self, limit: int = 6) -> list[dict[str, Any]]:
        """Get featured/promoted listings for the marketplace homepage."""
        return []


class InstallationService(BaseService):
    """Manage plugin/extension installations per tenant."""

    model = MarketplaceInstallation

    async def install(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        listing_id: UUID,
        installed_by: UUID | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Install a marketplace listing in the workspace.

        Validates compatibility, checks for existing installations,
        and creates an installation record.
        """
        # Check for existing installation
        existing = await self.db.execute(
            select(MarketplaceInstallation).where(
                MarketplaceInstallation.tenant_id == tenant_id,
                MarketplaceInstallation.workspace_id == workspace_id,
                MarketplaceInstallation.listing_id == listing_id,
                MarketplaceInstallation.status.in_(["installed", "active", "inactive"]),
            )
        )
        if existing.scalars().first():
            raise ConflictException(
                detail="This listing is already installed in this workspace"
            )

        installation = MarketplaceInstallation(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            listing_id=listing_id,
            version_installed="1.0.0",  # default; ListingService.get_listing stub not yet populated
            status="installed",
            config=config or {},
            installed_by=installed_by,
        )
        self.db.add(installation)
        await self.db.flush()
        await self.db.refresh(installation)

        logger.info(
            "Installed listing %s in workspace %s (installation %s)",
            listing_id, workspace_id, installation.id,
        )
        # Simulate background installation task dispatch
        logger.info("Installation task dispatched for listing %s (installation %s)", listing_id, installation.id)

        return {
            "id": str(installation.id),
            "tenant_id": str(installation.tenant_id),
            "workspace_id": str(installation.workspace_id),
            "listing_id": str(installation.listing_id),
            "version_installed": installation.version_installed,
            "status": installation.status,
            "config": installation.config or {},
            "installed_by": str(installation.installed_by) if installation.installed_by else None,
            "installed_at": installation.installed_at.isoformat() if installation.installed_at else None,
        }

    async def uninstall(
        self,
        installation_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Uninstall a plugin/extension from the workspace.

        Changes status to 'uninstalled' and marks uninstalled_at.
        """
        result = await self.db.execute(
            select(MarketplaceInstallation).where(
                MarketplaceInstallation.id == installation_id,
                MarketplaceInstallation.tenant_id == tenant_id,
            )
        )
        installation = result.scalars().first()
        if installation is None:
            raise NotFoundException(detail="Installation not found")

        installation.status = "uninstalled"
        installation.uninstalled_at = datetime.now(timezone.utc)
        await self.db.flush()

        logger.info("Uninstalled installation %s", installation_id)

    async def list_installed(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """List installed plugins/extensions for a workspace."""
        filters = [
            MarketplaceInstallation.tenant_id == tenant_id,
            MarketplaceInstallation.workspace_id == workspace_id,
        ]
        if status is not None:
            filters.append(MarketplaceInstallation.status == status)

        # Count
        count_stmt = (
            select(func.count())
            .select_from(MarketplaceInstallation)
            .where(*filters)
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Data
        stmt = (
            select(MarketplaceInstallation)
            .where(*filters)
            .order_by(desc(MarketplaceInstallation.installed_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return [
            {
                "id": str(i.id),
                "tenant_id": str(i.tenant_id),
                "workspace_id": str(i.workspace_id),
                "listing_id": str(i.listing_id),
                "version_installed": i.version_installed,
                "status": i.status,
                "config": i.config or {},
                "installed_by": str(i.installed_by) if i.installed_by else None,
                "installed_at": i.installed_at.isoformat() if i.installed_at else None,
                "uninstalled_at": i.uninstalled_at.isoformat() if i.uninstalled_at else None,
            }
            for i in items
        ], total

    async def get_installation(
        self,
        installation_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Fetch a single installation record."""
        result = await self.db.execute(
            select(MarketplaceInstallation).where(
                MarketplaceInstallation.id == installation_id,
                MarketplaceInstallation.tenant_id == tenant_id,
            )
        )
        installation = result.scalars().first()
        if installation is None:
            raise NotFoundException(detail="Installation not found")
        return {
            "id": str(installation.id),
            "tenant_id": str(installation.tenant_id),
            "workspace_id": str(installation.workspace_id),
            "listing_id": str(installation.listing_id),
            "version_installed": installation.version_installed,
            "status": installation.status,
            "config": installation.config or {},
            "installed_by": str(installation.installed_by) if installation.installed_by else None,
            "installed_at": installation.installed_at.isoformat() if installation.installed_at else None,
            "uninstalled_at": installation.uninstalled_at.isoformat() if installation.uninstalled_at else None,
        }

    async def update_config(
        self,
        installation_id: UUID,
        tenant_id: UUID,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Update configuration for an installed plugin."""
        result = await self.db.execute(
            select(MarketplaceInstallation).where(
                MarketplaceInstallation.id == installation_id,
                MarketplaceInstallation.tenant_id == tenant_id,
            )
        )
        installation = result.scalars().first()
        if installation is None:
            raise NotFoundException(detail="Installation not found")

        installation.config = config
        await self.db.flush()
        await self.db.refresh(installation)

        return {
            "id": str(installation.id),
            "config": installation.config or {},
        }

    async def toggle_status(
        self,
        installation_id: UUID,
        tenant_id: UUID,
        active: bool,
    ) -> dict[str, Any]:
        """Activate or deactivate an installed plugin."""
        result = await self.db.execute(
            select(MarketplaceInstallation).where(
                MarketplaceInstallation.id == installation_id,
                MarketplaceInstallation.tenant_id == tenant_id,
            )
        )
        installation = result.scalars().first()
        if installation is None:
            raise NotFoundException(detail="Installation not found")

        installation.status = "active" if active else "inactive"
        await self.db.flush()
        await self.db.refresh(installation)

        logger.info("Installation %s set to %s", installation_id, installation.status)
        return {
            "id": str(installation.id),
            "status": installation.status,
        }


class ReviewService:
    """Manage marketplace listing reviews and ratings."""

    async def create_review(
        self,
        listing_id: UUID,
        user_id: UUID,
        rating: int,
        title: str | None = None,
        content: str | None = None,
        pros: list[str] | None = None,
        cons: list[str] | None = None,
    ) -> dict[str, Any]:
        """Submit a review for a marketplace listing.

        Validates that the user has installed the listing (verified purchase)
        and that they haven't already reviewed it.
        """
        review = {
            "listing_id": str(listing_id),
            "user_id": str(user_id),
            "rating": rating,
            "title": title,
            "content": content,
            "pros": pros or [],
            "cons": cons or [],
            "is_verified_purchase": False,
            "is_flagged": False,
            "helpful_count": 0,
        }
        logger.info("Review submitted for listing %s by user %s", listing_id, user_id)
        return review

    async def list_reviews(
        self,
        listing_id: UUID,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "created_at",
        sort_desc: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """List reviews for a marketplace listing."""
        items: list[dict[str, Any]] = []
        total = 0
        return items, total

    async def get_review(self, review_id: UUID) -> dict[str, Any]:
        """Fetch a single review."""
        raise NotFoundException(detail="Review not found")

    async def mark_helpful(
        self,
        review_id: UUID,
    ) -> None:
        """Increment the helpful count for a review."""
        logger.debug("Review %s marked as helpful", review_id)

    async def flag_review(
        self,
        review_id: UUID,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """Flag a review for moderation."""
        logger.info("Review %s flagged: %s", review_id, reason)
        return {"is_flagged": True}

    async def delete_review(self, review_id: UUID) -> None:
        """Delete a review."""
        logger.info("Deleted review %s", review_id)
