"""
Marketplace router: plugin/extension listings, installation management,
billing integration, review system.

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
from app.schemas.marketplace import (
    ListingResponse,
    ReviewCreate,
    ReviewResponse,
    InstallationResponse,
)
from app.services.marketplace import (
    InstallationService,
    ListingService,
    ReviewService,
)

router = APIRouter(prefix="/marketplace", tags=["marketplace"])


# ── Listings ────────────────────────────────────────────────────────────────


@router.get("/listings")
async def list_listings(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    category: str | None = Query(None),
    search: str | None = Query(None),
    is_featured: bool | None = Query(None),
) -> dict:
    """List marketplace plugin/extension listings.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    skip = (page - 1) * limit
    service = ListingService(db)
    items, total = await service.list_listings(
        skip=skip,
        limit=limit,
        category=category,
        search=search,
        is_featured=is_featured,
    )
    return build_list_response(
        data=items,
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/listings/featured")
async def get_featured_listings(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(6, ge=1, le=20),
) -> dict:
    """Get featured marketplace listings.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = ListingService(db)
    items = await service.get_featured_listings(limit=limit)
    return build_single_response({"listings": items})


@router.get("/listings/{listing_id}")
async def get_listing(
    listing_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single marketplace listing with details.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = ListingService(db)
    listing = await service.get_listing(listing_id)
    return build_single_response(listing)


# ── Installations ───────────────────────────────────────────────────────────


@router.post("/install", status_code=201)
async def install_plugin(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    listing_id: UUID = Query(..., description="Marketplace listing ID to install"),
) -> dict:
    """Install a marketplace plugin/extension in the current workspace.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    service = InstallationService(db)
    installation = await service.install(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        listing_id=listing_id,
        installed_by=current_user.id,
    )
    return build_single_response(installation)


@router.get("/installed")
async def list_installed(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
) -> dict:
    """List installed plugins/extensions for the current workspace.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = getattr(request.state, "workspace_id", None)
    skip = (page - 1) * limit
    service = InstallationService(db)
    items, total = await service.list_installed(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        status=status,
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


@router.get("/installed/{installation_id}")
async def get_installation(
    installation_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single installation record.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = InstallationService(db)
    installation = await service.get_installation(
        installation_id, tenant_id=tenant_id,
    )
    return build_single_response(installation)


@router.patch("/installed/{installation_id}/toggle")
async def toggle_installation(
    installation_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    active: bool = Query(..., description="Set active/inactive"),
) -> dict:
    """Activate or deactivate an installed plugin.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = InstallationService(db)
    result = await service.toggle_status(
        installation_id, tenant_id=tenant_id, active=active,
    )
    return build_single_response(result)


@router.delete("/uninstall/{installation_id}", status_code=204)
async def uninstall_plugin(
    installation_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Uninstall a plugin/extension from the workspace."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = InstallationService(db)
    await service.uninstall(installation_id, tenant_id=tenant_id)
    return None


# ── Reviews ─────────────────────────────────────────────────────────────────


@router.post("/reviews", status_code=201)
async def create_review(
    body: ReviewCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Submit a review for a marketplace listing.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = ReviewService(db)
    review = await service.create_review(
        listing_id=body.listing_id,
        user_id=current_user.id,
        rating=body.rating,
        title=body.title,
        content=body.content,
        pros=body.pros,
        cons=body.cons,
    )
    return build_single_response(review)


@router.get("/listings/{listing_id}/reviews")
async def list_reviews(
    listing_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List reviews for a marketplace listing.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    skip = (page - 1) * limit
    service = ReviewService(db)
    items, total = await service.list_reviews(
        listing_id=listing_id,
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


@router.post("/reviews/{review_id}/helpful")
async def mark_review_helpful(
    review_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a review as helpful.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = ReviewService(db)
    await service.mark_helpful(review_id)
    return build_single_response({"success": True})
