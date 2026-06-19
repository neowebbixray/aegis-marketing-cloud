"""
Notifications router: in-app notifications, email notifications,
notification preferences, digest scheduling.

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
from app.schemas.notifications import (
    NotificationCreate,
    NotificationPreferencesCreate,
    NotificationPreferencesResponse,
    NotificationResponse,
    UnreadCountResponse,
)
from app.services.notifications import (
    DigestService,
    NotificationPreferencesService,
    NotificationService,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


# ── Notifications ───────────────────────────────────────────────────────────


@router.get("")
async def list_notifications(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    is_read: bool | None = Query(None),
    notification_type: str | None = Query(None),
    priority: str | None = Query(None),
) -> dict:
    """List notifications for the current user.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    skip = (page - 1) * limit
    service = NotificationService(db)
    items, total = await service.list_notifications(
        tenant_id=tenant_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        is_read=is_read,
        notification_type=notification_type,
        priority=priority,
    )
    return build_list_response(
        data=items,
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.patch("/{notification_id}")
async def mark_notification_read(
    notification_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a single notification as read.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = NotificationService(db)
    notification = await service.mark_read(
        notification_id,
        tenant_id=tenant_id,
        user_id=current_user.id,
    )
    return build_single_response(notification)


@router.post("/read-all")
async def mark_all_notifications_read(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark all unread notifications as read.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = NotificationService(db)
    count = await service.mark_all_read(
        tenant_id=tenant_id,
        user_id=current_user.id,
    )
    return build_single_response({"marked_read": count})


@router.get("/unread-count")
async def get_unread_count(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get unread notification count.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = NotificationService(db)
    counts = await service.get_unread_count(
        tenant_id=tenant_id,
        user_id=current_user.id,
    )
    return build_single_response(counts)


# ── Notification Preferences ────────────────────────────────────────────────


@router.get("/preferences")
async def get_notification_preferences(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get notification preferences for the current user.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = NotificationPreferencesService(db)
    prefs = await service.get_preferences(
        tenant_id=tenant_id,
        user_id=current_user.id,
    )
    return build_single_response(prefs)


@router.post("/preferences")
async def create_notification_preferences(
    body: NotificationPreferencesCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create or update notification preferences.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = NotificationPreferencesService(db)
    prefs = await service.create_preferences(
        tenant_id=tenant_id,
        user_id=current_user.id,
        channel=body.channel,
        notification_types=body.notification_types,
        enabled=body.enabled,
        digest_enabled=body.digest_enabled,
        digest_frequency=body.digest_frequency,
        quiet_hours_start=body.quiet_hours_start,
        quiet_hours_end=body.quiet_hours_end,
        email_address=body.email_address,
    )
    return build_single_response(prefs)


@router.patch("/preferences")
async def update_notification_preferences(
    body: NotificationPreferencesCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update notification preferences.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = NotificationPreferencesService(db)
    prefs = await service.update_preferences(
        tenant_id=tenant_id,
        user_id=current_user.id,
        **body.model_dump(exclude_unset=True),
    )
    return build_single_response(prefs)


# ── Digest ──────────────────────────────────────────────────────────────────


@router.post("/digest/generate")
async def generate_digest(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    frequency: str = Query("daily", regex=r"^(daily|weekly)$"),
) -> dict:
    """Generate a digest of unread notifications.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = DigestService(db)
    digest = await service.generate_digest(
        tenant_id=tenant_id,
        user_id=current_user.id,
        frequency=frequency,
    )
    return build_single_response(digest)


@router.post("/digest/schedule")
async def schedule_digest(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    frequency: str = Query("daily", regex=r"^(daily|weekly|never)$"),
) -> dict:
    """Schedule digest delivery preferences.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = DigestService(db)
    result = await service.schedule_digest(
        tenant_id=tenant_id,
        user_id=current_user.id,
        frequency=frequency,
    )
    return build_single_response(result)
