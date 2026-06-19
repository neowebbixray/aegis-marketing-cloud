"""
Notification REST endpoints — list, read, and manage in-app notifications.

All endpoints (except ``unread_count``) require authentication and respect
the tenant context via ``X-Tenant-ID`` header or the user's default tenant.

Responses use the standard ``{data, meta, links}`` envelope for lists and
``{data: {...}}`` for single resources.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.core.notification_service import NotificationService
from app.models.auth import User
from app.schemas.base import build_list_response, build_single_response
from app.schemas.notifications import (
    NotificationResponse,
    NotificationUpdate,
)

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", name="notification_list")
async def list_notifications(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
    notification_type: str | None = Query(None, max_length=50),
) -> dict:
    """List notifications for the authenticated user.

    Supports pagination, unread-only filtering, and optional type filter.
    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    service = NotificationService(db)
    notifications, total, unread_count = await service.get_notifications(
        user_id=current_user.id,
        page=page,
        per_page=per_page,
        unread_only=unread_only,
        notification_type=notification_type,
    )

    response = build_list_response(
        data=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        page=page,
        per_page=per_page,
        request=request,
    )
    # Include unread count in meta for convenience
    response["meta"]["unread_count"] = unread_count
    return response


@router.get("/unread-count", name="notification_unread_count")
async def get_unread_count(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the count of unread notifications for the authenticated user."""
    service = NotificationService(db)
    count = await service.get_unread_count(user_id=current_user.id)
    return {"data": {"unread_count": count}}


@router.get("/{notification_id}", name="notification_detail")
async def get_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single notification by ID.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = NotificationService(db)
    notification = await service.get_notification(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return build_single_response(NotificationResponse.model_validate(notification))


@router.post("/{notification_id}/read", name="notification_mark_read")
async def mark_notification_read(
    notification_id: UUID,
    body: NotificationUpdate = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Mark a single notification as read.

    Accepts an optional ``NotificationUpdate`` body (defaults to ``is_read=True``).
    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = NotificationService(db)
    notification = await service.mark_read(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return build_single_response(NotificationResponse.model_validate(notification))


@router.post("/read-all", name="notification_mark_all_read")
async def mark_all_notifications_read(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    workspace_id: str | None = Query(None),
) -> dict:
    """Mark all unread notifications as read for the authenticated user.

    Optionally scope to a specific workspace via ``workspace_id`` query param.
    Returns ``{data: {updated_count: N}}``.
    """
    service = NotificationService(db)
    ws_uuid = UUID(workspace_id) if workspace_id else None
    updated_count = await service.mark_all_read(
        user_id=current_user.id,
        workspace_id=ws_uuid,
    )
    return build_single_response({"updated_count": updated_count})


@router.delete("/{notification_id}", status_code=204, name="notification_delete")
async def delete_notification(
    notification_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete (soft-delete) a notification.

    Returns 204 No Content on success.
    """
    service = NotificationService(db)
    deleted = await service.delete_notification(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Notification not found")
