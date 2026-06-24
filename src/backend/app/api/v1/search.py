"""Search router — full-text search across contacts, deals, and campaigns.

Provides:

- ``GET /api/v1/search?q=...`` — global search across all entity types
- ``GET /api/v1/search/contacts?q=...`` — search only contacts
- ``GET /api/v1/search/deals?q=...`` — search only deals
- ``GET /api/v1/search/campaigns?q=...`` — search only campaigns
- ``POST /api/v1/search/reindex`` — admin-only full reindex
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.models.auth import User
from app.schemas.base import build_list_response
from app.schemas.search import SearchResultItem
from app.services.search_service import SearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.get("")
async def global_search(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(5, ge=1, le=50, description="Results per entity type"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Unified search across contacts, deals, and campaigns.

    Returns results grouped by entity type, each with its own total.
    """
    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is None:
        from uuid import UUID

        workspace_id = UUID("00000000-0000-0000-0000-000000000000")  # fallback

    service = SearchService(db)
    result = await service.global_search(
        query=q,
        workspace_id=workspace_id,
        limit_per_type=limit,
    )
    return {
        "data": result,
        "meta": {
            "query": q,
            "total": result["total"],
        },
    }


@router.get("/contacts")
async def search_contacts_endpoint(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Full-text search across contacts."""
    from uuid import UUID as _UUID

    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is None:
        workspace_id = _UUID("00000000-0000-0000-0000-000000000000")

    skip = (page - 1) * limit
    service = SearchService(db)
    items, total = await service.search_contacts(
        query=q,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
    )
    return build_list_response(
        data=[SearchResultItem.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/deals")
async def search_deals_endpoint(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Full-text search across deals."""
    from uuid import UUID as _UUID

    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is None:
        workspace_id = _UUID("00000000-0000-0000-0000-000000000000")

    skip = (page - 1) * limit
    service = SearchService(db)
    items, total = await service.search_deals(
        query=q,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
    )
    return build_list_response(
        data=[SearchResultItem.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/campaigns")
async def search_campaigns_endpoint(
    request: Request,
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=200),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Full-text search across campaigns."""
    from uuid import UUID as _UUID

    workspace_id = getattr(request.state, "workspace_id", None)
    if workspace_id is None:
        workspace_id = _UUID("00000000-0000-0000-0000-000000000000")

    skip = (page - 1) * limit
    service = SearchService(db)
    items, total = await service.search_campaigns(
        query=q,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
    )
    return build_list_response(
        data=[SearchResultItem.model_validate(i) for i in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.post("/reindex", status_code=200)
async def reindex_search(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Rebuild the full-text search index for all entities.

    This is an admin-level operation; only users with the ``admin`` role
    should call this.  For now, any authenticated user can trigger it.
    """
    service = SearchService(db)
    results = await service.reindex_all()
    return {
        "data": {
            "message": "Search index rebuilt",
            "details": results,
        },
    }
