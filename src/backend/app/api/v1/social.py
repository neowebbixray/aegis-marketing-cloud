"""
Social router: post scheduling, platform publishing, engagement metrics,
social listening.

All list responses use the docs-mandated ``{data, meta, links}`` envelope.
All single-resource responses use ``{data: {...}}``.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.auth import User
from app.schemas.base import build_list_response, build_single_response
from app.schemas.social import (
    PostCreate,
    PostResponse,
    PostUpdate,
    SocialAnalyticsResponse,
    MentionResponse,
)
from app.services.social import (
    SocialAnalyticsService,
    SocialListeningService,
    SocialPostService,
)

router = APIRouter(prefix="/social", tags=["social"])


# ── Posts ───────────────────────────────────────────────────────────────────


@router.get("/posts")
async def list_posts(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    platform: str | None = Query(None),
) -> dict:
    """List social media posts in the current workspace.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = SocialPostService(db)
    items, total = await service.list_posts(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
        status=status,
        platform=platform,
    )
    return build_list_response(
        data=items,
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.post("/posts", status_code=201)
async def create_post(
    body: PostCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new social media post.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = SocialPostService(db)
    post = await service.create_post(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        platform=body.platform,
        content=body.content,
        media_urls=body.media_urls,
        scheduled_at=body.scheduled_at,
        timezone=body.timezone,
        tags=body.tags,
        campaign_id=body.campaign_id,
        metadata=body.metadata,
    )
    return build_single_response(post)


@router.get("/posts/{post_id}")
async def get_post(
    post_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single social media post.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = SocialPostService(db)
    post = await service.get_post(post_id, tenant_id=tenant_id)
    return build_single_response(post)


@router.patch("/posts/{post_id}")
async def update_post(
    post_id: UUID,
    body: PostUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a social media post.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = SocialPostService(db)
    post = await service.update_post(
        post_id,
        tenant_id=tenant_id,
        **body.model_dump(exclude_unset=True),
    )
    return build_single_response(post)


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a social media post."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = SocialPostService(db)
    await service.delete_post(post_id, tenant_id=tenant_id)
    return None


@router.post("/posts/{post_id}/publish")
async def publish_post(
    post_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Publish a social media post immediately.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = SocialPostService(db)
    result = await service.publish_post(post_id, tenant_id=tenant_id)
    return build_single_response(result)


# ── Analytics ───────────────────────────────────────────────────────────────


@router.get("/analytics")
async def get_social_analytics(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    platform: str | None = Query(None),
    period_start: datetime | None = Query(None),
    period_end: datetime | None = Query(None),
) -> dict:
    """Get aggregated social media analytics.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = SocialAnalyticsService(db)
    analytics = await service.get_analytics(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        platform=platform,
        period_start=period_start,
        period_end=period_end,
    )
    return build_single_response(analytics)


# ── Mentions / Social Listening ─────────────────────────────────────────────


@router.get("/mentions")
async def list_mentions(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    platform: str | None = Query(None),
    sentiment: str | None = Query(None),
    is_flagged: bool | None = Query(None),
) -> dict:
    """List social mentions for the current workspace.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = SocialListeningService(db)
    items, total = await service.list_mentions(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
        platform=platform,
        sentiment=sentiment,
        is_flagged=is_flagged,
    )
    return build_list_response(
        data=items,
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


# ── Calendar ────────────────────────────────────────────────────────────────


@router.get("/calendar")
async def get_social_calendar(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    start_date: datetime | None = Query(None),
    end_date: datetime | None = Query(None),
    platform: str | None = Query(None),
) -> dict:
    """Get scheduled social posts for the content calendar.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = SocialPostService(db)
    entries = await service.get_calendar(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        start_date=start_date,
        end_date=end_date,
        platform=platform,
    )
    return build_single_response({"entries": entries})
