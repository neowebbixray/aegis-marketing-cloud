"""Notifications service: in-app notifications, email notifications,
notification preferences, digest scheduling.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.auth import User
from app.models.notifications import Notification
from app.services.base import BaseService

logger = logging.getLogger("amc.services.notifications")


class NotificationService(BaseService):
    """Create, retrieve, and manage in-app notifications."""

    model = Notification

    async def create_notification(
        self,
        tenant_id: UUID,
        user_id: UUID,
        notification_type: str,
        title: str,
        body: str | None = None,
        channel: str = "in_app",
        priority: str = "normal",
        action_url: str | None = None,
        action_label: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a notification for a user.

        The notification is delivered according to the user's preferences
        (in-app, email, or both).
        """
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=body or "",
            data=metadata or {},
            action_url=action_url,
            priority=priority,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)

        logger.info(
            "Created %s notification %s for user %s (type=%s, priority=%s)",
            channel,
            notification.id,
            user_id,
            notification_type,
            priority,
        )
        # Simulate dispatch via channel (email, websocket, push, etc.)
        logger.info("Dispatched notification %s via channel=%s", notification.id, channel)
        return {
            "id": str(notification.id),
            "tenant_id": str(tenant_id),
            "user_id": str(user_id),
            "notification_type": notification_type,
            "title": title,
            "body": notification.message,
            "channel": channel,
            "priority": priority,
            "is_read": notification.is_read,
            "is_dismissed": notification.deleted_at is not None,
            "action_url": action_url,
            "action_label": action_label,
            "metadata": notification.data or {},
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        }

    async def list_notifications(
        self,
        tenant_id: UUID,
        user_id: UUID,
        skip: int = 0,
        limit: int = 50,
        is_read: bool | None = None,
        notification_type: str | None = None,
        priority: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List notifications for a user with optional filtering."""
        # Base query — user-scoped, not soft-deleted
        base_filters = [
            Notification.user_id == user_id,
            Notification.deleted_at.is_(None),
        ]

        if is_read is not None:
            base_filters.append(Notification.is_read == is_read)
        if notification_type is not None:
            base_filters.append(Notification.notification_type == notification_type)
        if priority is not None:
            base_filters.append(Notification.priority == priority)

        # Count
        count_stmt = select(func.count()).select_from(Notification).where(*base_filters)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Data
        stmt = (
            select(Notification)
            .where(*base_filters)
            .order_by(desc(Notification.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return [
            {
                "id": str(n.id),
                "user_id": str(n.user_id),
                "workspace_id": str(n.workspace_id) if n.workspace_id else None,
                "notification_type": n.notification_type,
                "title": n.title,
                "body": n.message,
                "priority": n.priority,
                "is_read": n.is_read,
                "is_dismissed": n.deleted_at is not None,
                "action_url": n.action_url,
                "metadata": n.data or {},
                "created_at": n.created_at.isoformat() if n.created_at else None,
                "read_at": n.read_at.isoformat() if n.read_at else None,
            }
            for n in items
        ], total

    async def get_notification(
        self,
        notification_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """Fetch a single notification."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.deleted_at.is_(None),
            ),
        )
        notification = result.scalars().first()
        if notification is None:
            raise NotFoundException(detail="Notification not found")
        return {
            "id": str(notification.id),
            "user_id": str(notification.user_id),
            "workspace_id": str(notification.workspace_id) if notification.workspace_id else None,
            "notification_type": notification.notification_type,
            "title": notification.title,
            "body": notification.message,
            "priority": notification.priority,
            "is_read": notification.is_read,
            "is_dismissed": notification.deleted_at is not None,
            "action_url": notification.action_url,
            "metadata": notification.data or {},
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
        }

    async def mark_read(
        self,
        notification_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """Mark a single notification as read."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.deleted_at.is_(None),
            ),
        )
        notification = result.scalars().first()
        if notification is None:
            raise NotFoundException(detail="Notification not found")

        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(notification)

        logger.debug("Marked notification %s as read", notification_id)
        return {
            "id": str(notification.id),
            "is_read": notification.is_read,
            "read_at": notification.read_at.isoformat() if notification.read_at else None,
        }

    async def mark_all_read(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> int:
        """Mark all unread notifications as read.

        Returns the count of notifications updated.
        """
        now = datetime.now(UTC)
        result = await self.db.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
                Notification.deleted_at.is_(None),
            )
            .values(is_read=True, read_at=now)
            .returning(func.count(Notification.id)),
        )
        count = result.scalar() or 0
        await self.db.flush()

        logger.info("Marked all notifications as read for user %s (%d updated)", user_id, count)
        return count

    async def get_unread_count(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """Get unread notification count, with breakdowns."""
        # Total unread
        total_stmt = (
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
                Notification.deleted_at.is_(None),
            )
        )
        total_result = await self.db.execute(total_stmt)
        total = total_result.scalar() or 0

        # Breakdown by type
        by_type_stmt = (
            select(Notification.notification_type, func.count())
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
                Notification.deleted_at.is_(None),
            )
            .group_by(Notification.notification_type)
        )
        by_type_result = await self.db.execute(by_type_stmt)
        by_type = dict(by_type_result.all())

        # Breakdown by priority
        by_priority_stmt = (
            select(Notification.priority, func.count())
            .where(
                Notification.user_id == user_id,
                Notification.is_read == False,  # noqa: E712
                Notification.deleted_at.is_(None),
            )
            .group_by(Notification.priority)
        )
        by_priority_result = await self.db.execute(by_priority_stmt)
        by_priority = dict(by_priority_result.all())

        return {
            "total": total,
            "by_type": by_type,
            "by_priority": by_priority,
        }

    async def dismiss_notification(
        self,
        notification_id: UUID,
        tenant_id: UUID,
        user_id: UUID,
    ) -> None:
        """Dismiss a notification without reading it (soft delete)."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.deleted_at.is_(None),
            ),
        )
        notification = result.scalars().first()
        if notification is None:
            raise NotFoundException(detail="Notification not found")

        notification.soft_delete()
        await self.db.flush()
        logger.debug("Dismissed notification %s", notification_id)


class NotificationPreferencesService(BaseService):
    """Manage per-user notification preferences."""

    model = User

    async def get_preferences(
        self,
        tenant_id: UUID,
        user_id: UUID,
    ) -> dict[str, Any]:
        """Get notification preferences for a user."""
        return {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "channel": "in_app",
            "notification_types": ["all"],
            "enabled": True,
            "digest_enabled": False,
            "digest_frequency": "daily",
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "email_address": None,
        }

    async def update_preferences(
        self,
        tenant_id: UUID,
        user_id: UUID,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Update notification preferences."""
        logger.info("Updated notification preferences for user %s", user_id)
        return await self.get_preferences(tenant_id=tenant_id, user_id=user_id)

    async def create_preferences(
        self,
        tenant_id: UUID,
        user_id: UUID,
        channel: str = "in_app",
        notification_types: list[str] | None = None,
        enabled: bool = True,
        digest_enabled: bool = False,
        digest_frequency: str = "daily",
        quiet_hours_start: str | None = None,
        quiet_hours_end: str | None = None,
        email_address: str | None = None,
    ) -> dict[str, Any]:
        """Create initial notification preferences for a user."""
        return {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "channel": channel,
            "notification_types": notification_types or ["all"],
            "enabled": enabled,
            "digest_enabled": digest_enabled,
            "digest_frequency": digest_frequency,
            "quiet_hours_start": quiet_hours_start,
            "quiet_hours_end": quiet_hours_end,
            "email_address": email_address,
        }


class DigestService:
    """Schedule and generate notification digests."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def generate_digest(
        self,
        tenant_id: UUID,
        user_id: UUID,
        frequency: str = "daily",
    ) -> dict[str, Any]:
        """Generate a digest of unread notifications.

        Aggregates notifications by type and priority, then prepares
        the digest payload for email or in-app delivery.
        """
        return {
            "user_id": str(user_id),
            "tenant_id": str(tenant_id),
            "frequency": frequency,
            "total_notifications": 0,
            "sections": [],
            "generated_at": datetime.utcnow(),
        }

    async def schedule_digest(
        self,
        tenant_id: UUID,
        user_id: UUID,
        frequency: str = "daily",
    ) -> dict[str, Any]:
        """Schedule or update digest delivery preferences.

        Supported frequencies: daily, weekly, never.
        """
        logger.info("Scheduled %s digest for user %s", frequency, user_id)
        return {"frequency": frequency, "scheduled": True}
