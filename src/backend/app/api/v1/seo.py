"""
SEO router: keyword tracking, rank tracking, site audit, backlink analysis.

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
from app.schemas.seo import (
    KeywordCreate,
    KeywordResponse,
    KeywordUpdate,
    SiteAuditCreate,
    SiteAuditResponse,
    BacklinkResponse,
    BacklinkSummaryResponse,
)
from app.services.seo import BacklinkService, KeywordService, SiteAuditService

router = APIRouter(prefix="/seo", tags=["seo"])


# ── Keywords ─────────────────────────────────────────────────────────────────


@router.get("/keywords")
async def list_keywords(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(None),
    search_engine: str | None = Query(None),
) -> dict:
    """List tracked SEO keywords in the current workspace.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = KeywordService(db)
    items, total = await service.list_keywords(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
        search=search,
        search_engine=search_engine,
    )
    return build_list_response(
        data=items,
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.post("/keywords", status_code=201)
async def track_keyword(
    body: KeywordCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new keyword for ranking tracking.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = KeywordService(db)
    keyword = await service.track_keyword(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        keyword=body.keyword,
        target_url=body.target_url,
        search_engine=body.search_engine,
        location=body.location,
        language=body.language,
        tags=body.tags,
        **body.model_dump(exclude={"keyword", "target_url", "search_engine", "location", "language", "tags"}, exclude_none=True),
    )
    return build_single_response(keyword)


@router.get("/keywords/rankings")
async def get_keyword_rankings(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    keyword_ids: str | None = Query(None, description="Comma-separated keyword IDs"),
) -> dict:
    """Fetch current rankings for tracked keywords.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = KeywordService(db)
    kw_ids = [UUID(k.strip()) for k in keyword_ids.split(",")] if keyword_ids else None
    rankings = await service.get_keyword_rankings(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        keyword_ids=kw_ids,
    )
    return build_single_response({"rankings": rankings})


# ── Site Audit ──────────────────────────────────────────────────────────────


@router.post("/audit", status_code=201)
async def run_site_audit(
    body: SiteAuditCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Initiate an SEO site audit for a URL.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = SiteAuditService(db)
    audit = await service.run_audit(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        url=body.url,
        name=body.name,
        depth=body.depth,
        include_subdomains=body.include_subdomains,
        settings=body.settings,
    )
    return build_single_response(audit)


@router.get("/audits")
async def list_site_audits(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List site audits in the current workspace.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = SiteAuditService(db)
    items, total = await service.list_audits(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
    )
    return build_list_response(
        data=items,
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


# ── Backlinks ───────────────────────────────────────────────────────────────


@router.get("/backlinks")
async def list_backlinks(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    target_url: str | None = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List backlinks for the current workspace.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = BacklinkService(db)
    items, total = await service.list_backlinks(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        target_url=target_url,
        skip=skip,
        limit=limit,
    )
    return build_list_response(
        data=items,
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/backlinks/summary")
async def get_backlink_summary(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    target_url: str | None = Query(None),
) -> dict:
    """Get aggregated backlink statistics.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = BacklinkService(db)
    summary = await service.get_backlink_summary(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        target_url=target_url,
    )
    return build_single_response(summary)
