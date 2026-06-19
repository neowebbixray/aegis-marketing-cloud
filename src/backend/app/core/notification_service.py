"""
Notification service — creates, queries, and manages in-app notifications.

Each notification is persisted to the database and (optionally) broadcast
in real-time via the WebSocket ConnectionManager with Redis pub/sub so that
all worker processes can deliver the message to the right user or workspace.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notifications import Notification
from app.schemas.notifications import NotificationCreate, NotificationType

logger = logging.getLogger("amc.services.notification")


class NotificationService:
    """High-level notification business logic.

    All methods accept an optional ``current_user`` tuple for audit logging but
    do not enforce permissions — that is the responsibility of the API layer.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Create & Send ──────────────────────────────────────────────────────────

    async def send_notification(
        self,
        *,
        user_id: UUID,
        notification_type: NotificationType | str,
        title: str,
        message: str,
        data: dict[str, Any] | None = None,
        action_url: str | None = None,
        priority: str = "normal",
        workspace_id: UUID | None = None,
        broadcast_via_ws: bool = True,
    ) -> Notification:
        """Create a notification record and optionally broadcast it via WebSocket.

        Args:
            user_id: The recipient user's UUID.
            notification_type: A ``NotificationType`` enum value or string.
            title: Short notification title.
            message: Notification body text.
            data: Arbitrary JSON-serialisable payload.
            action_url: Optional deep-link URL for the notification.
            priority: One of ``low``, ``normal``, ``high``, ``critical``.
            workspace_id: Optional workspace scope.
            broadcast_via_ws: Whether to also deliver the notification over
                WebSocket immediately.

        Returns:
            The created ``Notification`` ORM instance.
        """
        if isinstance(notification_type, NotificationType):
            notification_type = notification_type.value

        notification = Notification(
            user_id=user_id,
            workspace_id=workspace_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data or {},
            action_url=action_url,
            priority=priority,
            is_read=False,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(notification)

        logger.info(
            "Notification created: id=%s user=%s type=%s",
            notification.id,
            user_id,
            notification_type,
        )

        if broadcast_via_ws:
            await self._broadcast_notification(notification)

        return notification

    async def _broadcast_notification(self, notification: Notification) -> None:
        """Deliver a notification over WebSocket (with Redis pub/sub).

        Uses the global ``connection_manager`` singleton so the message
        reaches the target user regardless of which worker process they
        are connected to.
        """
        try:
            from app.core.websocket import connection_manager

            ws_message = {
                "type": "notification",
                "payload": {
                    "id": str(notification.id),
                    "user_id": str(notification.user_id),
                    "workspace_id": str(notification.workspace_id)
                    if notification.workspace_id
                    else None,
                    "notification_type": notification.notification_type,
                    "title": notification.title,
                    "message": notification.message,
                    "data": notification.data or {},
                    "action_url": notification.action_url,
                    "priority": notification.priority,
                    "is_read": notification.is_read,
                    "created_at": notification.created_at.isoformat()
                    if notification.created_at
                    else None,
                },
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "notification_id": str(notification.id),
            }

            # Publish to Redis for cross-process delivery
            await connection_manager.publish_notification(
                user_id=str(notification.user_id),
                message=ws_message,
                workspace_id=str(notification.workspace_id)
                if notification.workspace_id
                else None,
            )

            # Also send directly to any locally-connected client
            await connection_manager.send_personal_message(
                str(notification.user_id), ws_message
            )

        except Exception:
            logger.warning(
                "Failed to broadcast notification %s via WebSocket",
                notification.id,
                exc_info=True,
            )

    # ── Queries ────────────────────────────────────────────────────────────────

    async def get_notifications(
        self,
        user_id: UUID,
        *,
        page: int = 1,
        per_page: int = 50,
        unread_only: bool = False,
        notification_type: str | None = None,
        workspace_id: UUID | None = None,
    ) -> tuple[list[Notification], int, int]:
        """Fetch notifications for a user with pagination.

        Args:
            user_id: The user whose notifications to fetch.
            page: Page number (1-indexed).
            per_page: Items per page (max 200).
            unread_only: If True, only return unread notifications.
            notification_type: Optional filter by notification type.
            workspace_id: Optional filter by workspace.

        Returns:
            A tuple of ``(notifications, total_count, unread_count)``.
        """
        # Build the base filter
        filters = [Notification.user_id == user_id]

        if unread_only:
            filters.append(Notification.is_read == False)  # noqa: E712

        if notification_type:
            filters.append(Notification.notification_type == notification_type)

        if workspace_id:
            filters.append(Notification.workspace_id == workspace_id)

        # Count total matching records
        count_stmt = select(func.count()).select_from(Notification).where(*filters)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Count unread (without the unread_only filter)
        unread_filters = [
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        ]
        if workspace_id:
            unread_filters.append(Notification.workspace_id == workspace_id)
        unread_stmt = (
            select(func.count()).select_from(Notification).where(*unread_filters)
        )
        unread_result = await self.db.execute(unread_stmt)
        unread_count = unread_result.scalar() or 0

        # Fetch the page
        offset = (page - 1) * per_page
        query = (
            select(Notification)
            .where(*filters)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        return notifications, total, unread_count

    async def get_notification(
        self, notification_id: UUID, user_id: UUID
    ) -> Notification | None:
        """Get a single notification by ID, scoped to the user.

        Returns ``None`` if not found or not owned by the user.
        """
        stmt = select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalars().first()

    # ── Mark Read ──────────────────────────────────────────────────────────────

    async def mark_read(
        self, notification_id: UUID, user_id: UUID
    ) -> Notification | None:
        """Mark a single notification as read.

        Returns the updated notification, or ``None`` if not found.
        """
        notification = await self.get_notification(notification_id, user_id)
        if notification is None:
            return None

        notification.is_read = True
        notification.read_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(notification)

        return notification

    async def mark_all_read(
        self,
        user_id: UUID,
        workspace_id: UUID | None = None,
    ) -> int:
        """Mark all unread notifications as read for the given user.

        Args:
            user_id: The user whose notifications to mark.
            workspace_id: Optional scope to a specific workspace.

        Returns:
            The number of notifications updated.
        """
        filters = [
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        ]
        if workspace_id:
            filters.append(Notification.workspace_id == workspace_id)

        stmt = (
            update(Notification)
            .where(*filters)
            .values(
                is_read=True,
                read_at=datetime.now(timezone.utc),
            )
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        updated_count = result.rowcount
        logger.info(
            "Marked %d notifications as read for user %s",
            updated_count,
            user_id,
        )
        return updated_count

    # ── Delete ─────────────────────────────────────────────────────────────────

    async def delete_notification(
        self, notification_id: UUID, user_id: UUID
    ) -> bool:
        """Soft-delete a notification.

        Returns ``True`` if deleted, ``False`` if not found.
        """
        notification = await self.get_notification(notification_id, user_id)
        if notification is None:
            return False

        notification.soft_delete()
        await self.db.flush()
        await self.db.commit()
        return True

    async def get_unread_count(
        self,
        user_id: UUID,
        workspace_id: UUID | None = None,
    ) -> int:
        """Get the count of unread notifications for a user."""
        filters = [
            Notification.user_id == user_id,
            Notification.is_read == False,  # noqa: E712
        ]
        if workspace_id:
            filters.append(Notification.workspace_id == workspace_id)

        stmt = select(func.count()).select_from(Notification).where(*filters)
        result = await self.db.execute(stmt)
        return result.scalar() or 0
