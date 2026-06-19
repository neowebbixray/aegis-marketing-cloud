"""
Knowledge Base router: articles, categories, search, versioning.

All list responses use the docs-mandated ``{data, meta, links}`` envelope.
All single-resource responses use ``{data: {...}}``.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.auth import User
from app.schemas.base import build_list_response, build_single_response
from app.schemas.knowledge_base import (
    ArticleCreate,
    ArticleResponse,
    ArticleUpdate,
    ArticleVersionResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    SearchResponse,
)
from app.services.knowledge_base import (
    ArticleService,
    CategoryService,
    SearchService,
)

router = APIRouter(prefix="/knowledge-base", tags=["knowledge-base"])


# ── Articles ────────────────────────────────────────────────────────────────


@router.get("/articles")
async def list_articles(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    category_id: UUID | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
) -> dict:
    """List knowledge base articles.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = ArticleService(db)
    items, total = await service.list_articles(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
        category_id=category_id,
        status=status,
        search=search,
    )
    return build_list_response(
        data=items,
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.post("/articles", status_code=201)
async def create_article(
    body: ArticleCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new knowledge base article.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = ArticleService(db)
    article = await service.create_article(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        title=body.title,
        content=body.content,
        category_id=body.category_id,
        tags=body.tags,
        status=body.status,
        is_internal=body.is_internal,
        author_id=body.author_id,
        seo_meta=body.seo_meta,
        metadata=body.metadata,
    )
    return build_single_response(article)


@router.get("/articles/{article_id}")
async def get_article(
    article_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single knowledge base article.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ArticleService(db)
    article = await service.get_article(article_id, tenant_id=tenant_id)
    return build_single_response(article)


@router.patch("/articles/{article_id}")
async def update_article(
    article_id: UUID,
    body: ArticleUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a knowledge base article.

    If content changes, a new version is automatically created.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ArticleService(db)
    article = await service.update_article(
        article_id,
        tenant_id=tenant_id,
        **body.model_dump(exclude_unset=True),
    )
    return build_single_response(article)


@router.delete("/articles/{article_id}", status_code=204)
async def delete_article(
    article_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a knowledge base article."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ArticleService(db)
    await service.delete_article(article_id, tenant_id=tenant_id)
    return None


@router.post("/articles/{article_id}/helpful")
async def mark_article_helpful(
    article_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    is_helpful: bool = Query(..., description="Was this article helpful?"),
) -> dict:
    """Record whether an article was helpful.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ArticleService(db)
    await service.mark_helpful(
        article_id, tenant_id=tenant_id, is_helpful=is_helpful,
    )
    return build_single_response({"success": True})


@router.get("/articles/{article_id}/versions")
async def list_article_versions(
    article_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all versions of an article.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = ArticleService(db)
    versions = await service.list_versions(article_id, tenant_id=tenant_id)
    return build_single_response({"versions": versions})


# ── Categories ──────────────────────────────────────────────────────────────


@router.get("/categories")
async def list_categories(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """List all knowledge base categories.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = CategoryService(db)
    categories = await service.list_categories(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
    )
    return build_single_response({"categories": categories})


@router.post("/categories", status_code=201)
async def create_category(
    body: CategoryCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new knowledge base category.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = CategoryService(db)
    category = await service.create_category(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        parent_id=body.parent_id,
        icon=body.icon,
        sort_order=body.sort_order,
    )
    return build_single_response(category)


@router.patch("/categories/{category_id}")
async def update_category(
    category_id: UUID,
    body: CategoryUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a knowledge base category.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = CategoryService(db)
    category = await service.update_category(
        category_id,
        tenant_id=tenant_id,
        **body.model_dump(exclude_unset=True),
    )
    return build_single_response(category)


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a knowledge base category."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = CategoryService(db)
    await service.delete_category(category_id, tenant_id=tenant_id)
    return None


# ── Search ──────────────────────────────────────────────────────────────────


@router.get("/search")
async def search_articles(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    query: str = Query(..., min_length=1),
    category_id: UUID | None = Query(None),
    tags: str | None = Query(None, description="Comma-separated tags"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Search knowledge base articles.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = SearchService(db)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    results = await service.search(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        query=query,
        category_id=category_id,
        tags=tag_list,
        skip=skip,
        limit=limit,
    )
    return build_single_response(results)
