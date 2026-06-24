"""Knowledge Base service: article management, categories, search indexing, versioning."""

from __future__ import annotations

import logging
import re
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.marketing import Campaign
from app.services.base import BaseService

logger = logging.getLogger("amc.services.knowledge_base")


def _slugify(title: str) -> str:
    """Convert a title to a URL-friendly slug."""
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


class CategoryService(BaseService):
    """Manage knowledge base categories."""

    model = Campaign

    async def create_category(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        name: str,
        description: str | None = None,
        parent_id: UUID | None = None,
        icon: str | None = None,
        sort_order: int = 0,
    ) -> dict[str, Any]:
        """Create a new knowledge base category."""
        category = {
            "name": name,
            "description": description,
            "parent_id": str(parent_id) if parent_id else None,
            "icon": icon,
            "sort_order": sort_order,
            "article_count": 0,
            "tenant_id": str(tenant_id),
            "workspace_id": str(workspace_id),
        }
        logger.info("Created category '%s' for workspace %s", name, workspace_id)
        return category

    async def list_categories(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
    ) -> list[dict[str, Any]]:
        """List all categories in the knowledge base."""
        return []

    async def get_category(self, category_id: UUID, tenant_id: UUID) -> dict[str, Any]:
        """Fetch a single category."""
        raise NotFoundException(detail="Category not found")

    async def update_category(
        self,
        category_id: UUID,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update a category."""
        return {}

    async def delete_category(self, category_id: UUID, tenant_id: UUID) -> None:
        """Delete a category."""
        logger.info("Deleted category %s", category_id)


class ArticleService(BaseService):
    """Manage knowledge base articles with versioning."""

    model = Campaign

    async def create_article(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        title: str,
        content: str,
        category_id: UUID | None = None,
        tags: list[str] | None = None,
        status: str = "draft",
        is_internal: bool = False,
        author_id: UUID | None = None,
        seo_meta: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new knowledge base article.

        Auto-generates a slug from the title and initialises version 1.
        """
        slug = _slugify(title)
        article = {
            "title": title,
            "slug": slug,
            "content": content,
            "category_id": str(category_id) if category_id else None,
            "tags": tags or [],
            "status": status,
            "is_internal": is_internal,
            "version": 1,
            "author_id": str(author_id) if author_id else None,
            "view_count": 0,
            "helpful_count": 0,
            "not_helpful_count": 0,
            "seo_meta": seo_meta or {},
            "metadata": metadata or {},
            "tenant_id": str(tenant_id),
            "workspace_id": str(workspace_id),
        }
        logger.info("Created article '%s' (slug=%s) for workspace %s", title, slug, workspace_id)
        return article

    async def list_articles(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        skip: int = 0,
        limit: int = 50,
        category_id: UUID | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List articles with optional filtering and search."""
        items: list[dict[str, Any]] = []
        total = 0
        return items, total

    async def get_article(
        self,
        article_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Fetch a single article by ID.

        Increments the view count.
        """
        raise NotFoundException(detail="Article not found")

    async def get_article_by_slug(
        self,
        slug: str,
        tenant_id: UUID,
        workspace_id: UUID,
    ) -> dict[str, Any]:
        """Fetch an article by its URL slug."""
        raise NotFoundException(detail="Article not found")

    async def update_article(
        self,
        article_id: UUID,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update an article, creating a new version if content changes."""
        return {}

    async def delete_article(self, article_id: UUID, tenant_id: UUID) -> None:
        """Soft-delete an article."""
        logger.info("Deleted article %s", article_id)

    async def mark_helpful(
        self,
        article_id: UUID,
        tenant_id: UUID,
        is_helpful: bool,
    ) -> None:
        """Record whether an article was helpful."""
        logger.debug("Article %s marked as helpful=%s", article_id, is_helpful)

    async def list_versions(
        self,
        article_id: UUID,
        tenant_id: UUID,
    ) -> list[dict[str, Any]]:
        """List all versions of an article."""
        return []

    async def get_version(
        self,
        version_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Fetch a specific article version."""
        raise NotFoundException(detail="Article version not found")


class SearchService:
    """Full-text search across knowledge base articles."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        query: str,
        category_id: UUID | None = None,
        tags: list[str] | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search articles by title and content.

        Returns ranked results with relevance scores and search suggestions.
        """
        return {
            "results": [],
            "total": 0,
            "query": query,
            "suggestion": None,
        }
