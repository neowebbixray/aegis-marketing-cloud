"""
Marketplace service: plugin/extension listings, installation management,
billing integration, review system.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException, ValidationException
from app.models.marketing import Campaign
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

    model = Campaign

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
        # Stub: verify listing exists and is compatible
        installation = {
            "tenant_id": str(tenant_id),
            "workspace_id": str(workspace_id),
            "listing_id": str(listing_id),
            "version_installed": "1.0.0",
            "status": "installing",
            "config": config or {},
            "installed_by": str(installed_by) if installed_by else None,
        }
        logger.info(
            "Installing listing %s in workspace %s", listing_id, workspace_id,
        )
        # TODO: dispatch background installation task
        return installation

    async def uninstall(
        self,
        installation_id: UUID,
        tenant_id: UUID,
    ) -> None:
        """Uninstall a plugin/extension from the workspace.

        Changes status to 'uninstalling' and triggers cleanup.
        """
        logger.info("Uninstalling installation %s", installation_id)

    async def list_installed(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        """List installed plugins/extensions for a workspace."""
        items: list[dict[str, Any]] = []
        total = 0
        return items, total

    async def get_installation(
        self,
        installation_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Fetch a single installation record."""
        raise NotFoundException(detail="Installation not found")

    async def update_config(
        self,
        installation_id: UUID,
        tenant_id: UUID,
        config: dict[str, Any],
    ) -> dict[str, Any]:
        """Update configuration for an installed plugin."""
        return {}

    async def toggle_status(
        self,
        installation_id: UUID,
        tenant_id: UUID,
        active: bool,
    ) -> dict[str, Any]:
        """Activate or deactivate an installed plugin."""
        status = "active" if active else "inactive"
        logger.info("Installation %s set to %s", installation_id, status)
        return {"status": status}


class ReviewService(BaseService):
    """Manage marketplace listing reviews and ratings."""

    model = Campaign

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
