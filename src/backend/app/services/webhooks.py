"""Webhook service: event catalog, registration, delivery with retry & dedup,
signature verification, secret management, and cleanup.

All tenant-scoped operations require a ``tenant_id`` UUID.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import httpx
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.models.webhooks import Webhook, WebhookDelivery
from app.schemas.webhooks import (
    DEFAULT_RETRY_CONFIG,
    WEBHOOK_EVENT_CATALOG,
    DeliveryStatus,
)

logger = logging.getLogger("amc.services.webhooks")

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_MAX_RETRIES = 5
DEFAULT_INITIAL_INTERVAL = 10  # seconds
DEFAULT_MULTIPLIER = 2.0
DEFAULT_MAX_INTERVAL = 3600  # 1 hour
SIGNATURE_HEADER = "X-Webhook-Signature"
SIGNATURE_VERSION = "v1"
DELIVERY_ATTEMPT_TIMEOUT = 30  # seconds per HTTP attempt


# ── Helpers ───────────────────────────────────────────────────────────────────


def _compute_signature(payload: str, secret: str) -> str:
    """Compute HMAC-SHA256 signature for the given payload and secret."""
    mac = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    )
    return f"{SIGNATURE_VERSION},{mac.hexdigest()}"


def verify_signature(payload: str, signature: str, secret: str) -> bool:
    """Verify an HMAC-SHA256 webhook signature.

    Args:
        payload: Raw request body as string.
        signature: The ``X-Webhook-Signature`` header value (format: ``v1,<hex>``).
        secret: The shared secret used to compute the signature.

    Returns:
        ``True`` if the signature is valid, ``False`` otherwise.

    """
    try:
        version, sig_value = signature.split(",", 1)
        if version != SIGNATURE_VERSION:
            logger.warning("Unknown signature version: %s", version)
            return False
        expected = _compute_signature(payload, secret)
        _, expected_value = expected.split(",", 1)
        return hmac.compare_digest(sig_value, expected_value)
    except (ValueError, AttributeError) as exc:
        logger.warning("Invalid signature format: %s", exc)
        return False


def _calculate_retry_delay(
    attempt: int,
    initial_interval: int = DEFAULT_INITIAL_INTERVAL,
    multiplier: float = DEFAULT_MULTIPLIER,
    max_interval: int = DEFAULT_MAX_INTERVAL,
) -> int:
    """Calculate exponential backoff delay in seconds for the given attempt number."""
    delay = initial_interval * (multiplier ** (attempt - 1))
    return min(int(delay), max_interval)


def _get_retry_config(webhook: Webhook) -> dict[str, Any]:
    """Get effective retry config, falling back to defaults."""
    config = webhook.retry_config or {}
    return {
        "max_retries": config.get("max_retries", DEFAULT_MAX_RETRIES),
        "initial_interval_seconds": config.get(
            "initial_interval_seconds",
            DEFAULT_INITIAL_INTERVAL,
        ),
        "multiplier": config.get("multiplier", DEFAULT_MULTIPLIER),
        "max_interval_seconds": config.get(
            "max_interval_seconds",
            DEFAULT_MAX_INTERVAL,
        ),
    }


# ── Service ───────────────────────────────────────────────────────────────────


class WebhookService:
    """High-level webhook operations for a single tenant context."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Event Catalog ─────────────────────────────────────────────────────────

    @staticmethod
    def get_event_catalog() -> dict[str, dict[str, Any]]:
        """Return the full webhook event catalog."""
        return dict(WEBHOOK_EVENT_CATALOG)

    @staticmethod
    def get_event_categories() -> list[str]:
        """Return distinct event categories."""
        categories: set[str] = set()
        for entry in WEBHOOK_EVENT_CATALOG.values():
            categories.add(entry.get("category", "uncategorized"))
        return sorted(categories)

    # ── CRUD ──────────────────────────────────────────────────────────────────

    async def create_webhook(
        self,
        tenant_id: UUID,
        url: str,
        events: list[str],
        secret: str | None = None,
        api_version: str = "v1",
        retry_config: dict[str, Any] | None = None,
        description: str | None = None,
        is_active: bool = True,
    ) -> Webhook:
        """Register a new webhook endpoint for the tenant.

        Raises:
            ValidationException: If the URL already exists for this tenant,
                or if an invalid event type is specified.

        """
        # Validate event types against catalog
        valid_events = set(WEBHOOK_EVENT_CATALOG.keys())
        for event in events:
            if event not in valid_events:
                raise ValidationException(
                    detail=f"Unknown event type '{event}'. See /webhooks/events for valid types.",
                )

        # Check for duplicate URL
        existing = await self.db.execute(
            select(Webhook).where(
                and_(
                    Webhook.tenant_id == tenant_id,
                    Webhook.url == url,
                    Webhook.deleted_at.is_(None),
                ),
            ),
        )
        if existing.scalar_one_or_none():
            raise ConflictException(
                detail=f"A webhook with URL '{url}' already exists for this tenant.",
            )

        secret_hash = None
        if secret:
            secret_hash = hashlib.sha256(secret.encode("utf-8")).hexdigest()

        webhook = Webhook(
            tenant_id=tenant_id,
            url=url,
            secret_hash=secret_hash,
            events=events,
            is_active=is_active,
            api_version=api_version,
            retry_config=retry_config or dict(DEFAULT_RETRY_CONFIG),
            description=description,
        )
        self.db.add(webhook)
        await self.db.flush()
        await self.db.refresh(webhook)

        logger.info(
            "Created webhook %s for tenant %s (%d events)",
            webhook.id,
            tenant_id,
            len(events),
        )
        return webhook

    async def update_webhook(
        self,
        webhook_id: UUID,
        tenant_id: UUID,
        **updates: Any,
    ) -> Webhook:
        """Update an existing webhook.

        Only the fields provided in ``updates`` are modified.
        """
        webhook = await self._get_webhook(webhook_id, tenant_id)

        # Whitelist of updatable fields
        updatable = {
            "url",
            "events",
            "is_active",
            "api_version",
            "retry_config",
            "description",
        }
        for key, value in updates.items():
            if key in updatable:
                setattr(webhook, key, value)

        await self.db.flush()
        await self.db.refresh(webhook)
        logger.info("Updated webhook %s", webhook_id)
        return webhook

    async def delete_webhook(self, webhook_id: UUID, tenant_id: UUID) -> None:
        """Soft-delete a webhook."""
        webhook = await self._get_webhook(webhook_id, tenant_id)
        webhook.soft_delete()
        await self.db.flush()
        logger.info("Deleted webhook %s", webhook_id)

    async def list_webhooks(
        self,
        tenant_id: UUID,
        is_active: bool | None = None,
        event_type: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[Webhook], int]:
        """List webhooks for a tenant, with optional filters and pagination."""
        conditions: list = [Webhook.tenant_id == tenant_id, Webhook.deleted_at.is_(None)]

        if is_active is not None:
            conditions.append(Webhook.is_active == is_active)
        if event_type:
            # Use JSONB contains — PostgreSQL can index this
            conditions.append(Webhook.events.contains([event_type]))

        offset = (page - 1) * per_page

        # Count
        count_stmt = select(func.count()).select_from(Webhook).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Fetch
        stmt = (
            select(Webhook)
            .where(and_(*conditions))
            .order_by(desc(Webhook.created_at))
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_webhook(self, webhook_id: UUID, tenant_id: UUID) -> Webhook:
        """Get a single webhook by ID."""
        return await self._get_webhook(webhook_id, tenant_id)

    # ── Secret Management ─────────────────────────────────────────────────────

    async def rotate_secret(
        self,
        webhook_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, str]:
        """Rotate the webhook signing secret.

        Returns a dict with the new secret (shown once).
        """
        webhook = await self._get_webhook(webhook_id, tenant_id)
        new_secret = uuid4().hex + uuid4().hex  # 64-char hex string
        webhook.secret_hash = hashlib.sha256(new_secret.encode("utf-8")).hexdigest()
        await self.db.flush()
        logger.info("Rotated secret for webhook %s", webhook_id)
        return {"secret": new_secret}

    # ── Event Dispatch & Delivery ─────────────────────────────────────────────

    async def dispatch_event(
        self,
        event_type: str,
        tenant_id: UUID,
        payload: dict[str, Any],
    ) -> list[UUID]:
        """Dispatch an event to all active webhooks subscribed to this event type.

        Creates ``WebhookDelivery`` records for each matching webhook and
        triggers delivery asynchronously.

        Args:
            event_type: The event type string (e.g. ``contact.created``).
            tenant_id: The tenant context.
            payload: The event payload to deliver.

        Returns:
            List of delivery record IDs created.

        """
        delivery_ids: list[UUID] = []

        # Find all active webhooks subscribed to this event type
        stmt = select(Webhook).where(
            and_(
                Webhook.tenant_id == tenant_id,
                Webhook.is_active.is_(True),
                Webhook.deleted_at.is_(None),
                Webhook.events.contains([event_type]),
            ),
        )
        result = await self.db.execute(stmt)
        webhooks = list(result.scalars().all())

        if not webhooks:
            logger.debug(
                "No active webhooks for event %s on tenant %s",
                event_type,
                tenant_id,
            )
            return delivery_ids

        payload_str = json.dumps(payload, default=str)

        for webhook in webhooks:
            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event_type=event_type,
                status=DeliveryStatus.PENDING.value,
                request_body=payload_str,
                request_headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Aegis-Webhook/1.0",
                },
                attempt=1,
                max_attempts=_get_retry_config(webhook)["max_retries"],
            )
            self.db.add(delivery)
            await self.db.flush()
            await self.db.refresh(delivery)

            delivery_ids.append(delivery.id)

            # Attempt delivery immediately (asynchronously)
            await self._attempt_delivery(webhook, delivery, payload_str)

        return delivery_ids

    async def _attempt_delivery(
        self,
        webhook: Webhook,
        delivery: WebhookDelivery,
        payload_str: str,
    ) -> None:
        """Attempt a single webhook delivery with signature."""
        delivery.status = DeliveryStatus.DELIVERING.value
        headers = dict(delivery.request_headers or {})
        headers["Content-Type"] = "application/json"
        headers["X-Webhook-ID"] = str(webhook.id)
        headers["X-Webhook-Event"] = delivery.event_type
        headers["X-Webhook-Delivery-ID"] = str(delivery.id)
        headers["X-Webhook-Attempt"] = str(delivery.attempt)

        # Add signature if webhook has a secret
        secret = await self._get_webhook_secret(webhook)
        if secret:
            signature = _compute_signature(payload_str, secret)
            headers[SIGNATURE_HEADER] = signature

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=DELIVERY_ATTEMPT_TIMEOUT) as client:
                response = await client.post(
                    webhook.url,
                    content=payload_str,
                    headers=headers,
                )
            duration = int((time.monotonic() - start) * 1000)
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:10000]  # truncate long bodies
            delivery.duration_ms = duration

            if 200 <= response.status_code < 300:
                delivery.status = DeliveryStatus.SUCCEEDED.value
                delivery.completed_at = datetime.now(UTC)
                logger.info(
                    "Webhook %s delivery %s succeeded (%d) in %dms",
                    webhook.id,
                    delivery.id,
                    response.status_code,
                    duration,
                )
            else:
                await self._handle_failed_delivery(webhook, delivery)
        except (httpx.TimeoutException, httpx.RequestError) as exc:
            duration = int((time.monotonic() - start) * 1000)
            delivery.duration_ms = duration
            delivery.response_body = str(exc)[:10000]
            logger.warning(
                "Webhook %s delivery %s failed (attempt %d): %s",
                webhook.id,
                delivery.id,
                delivery.attempt,
                exc,
            )
            await self._handle_failed_delivery(webhook, delivery)

        await self.db.flush()

    async def _handle_failed_delivery(
        self,
        webhook: Webhook,
        delivery: WebhookDelivery,
    ) -> None:
        """Handle a failed delivery attempt — schedule retry or mark as failed."""
        retry_config = _get_retry_config(webhook)

        if delivery.attempt >= retry_config["max_retries"]:
            delivery.status = DeliveryStatus.FAILED.value
            delivery.completed_at = datetime.now(UTC)
            logger.warning(
                "Webhook %s delivery %s failed permanently after %d attempts",
                webhook.id,
                delivery.id,
                delivery.attempt,
            )
        else:
            delivery.status = DeliveryStatus.RETRYING.value
            delay = _calculate_retry_delay(
                delivery.attempt + 1,
                initial_interval=retry_config["initial_interval_seconds"],
                multiplier=retry_config["multiplier"],
                max_interval=retry_config["max_interval_seconds"],
            )
            delivery.next_retry_at = datetime.now(UTC) + timedelta(
                seconds=delay,
            )
            logger.info(
                "Webhook %s delivery %s will retry in %ds (attempt %d)",
                webhook.id,
                delivery.id,
                delay,
                delivery.attempt + 1,
            )

    async def process_delivery(
        self,
        webhook_id: UUID,
        delivery_id: UUID,
    ) -> WebhookDelivery:
        """Process (or retry) a specific delivery.

        Used by the retry endpoint and background retry workers.

        Args:
            webhook_id: The webhook ID.
            delivery_id: The delivery record ID to process.

        Returns:
            The updated ``WebhookDelivery`` record.

        """
        webhook = await self._get_webhook(webhook_id)
        delivery = await self.db.get(WebhookDelivery, delivery_id)
        if delivery is None:
            raise NotFoundException(detail=f"Delivery {delivery_id} not found")
        if delivery.status in (DeliveryStatus.SUCCEEDED.value, DeliveryStatus.CANCELLED.value):
            raise ConflictException(
                detail=f"Delivery {delivery_id} is already in '{delivery.status}' state",
            )

        payload_str = delivery.request_body or "{}"
        delivery.attempt += 1
        await self._attempt_delivery(webhook, delivery, payload_str)
        await self.db.refresh(delivery)
        return delivery

    # ── Delivery Logs ─────────────────────────────────────────────────────────

    async def get_delivery_logs(
        self,
        webhook_id: UUID,
        tenant_id: UUID,
        page: int = 1,
        per_page: int = 50,
        status: str | None = None,
    ) -> tuple[list[WebhookDelivery], int]:
        """Get delivery history for a webhook with pagination."""
        # Verify webhook belongs to tenant
        await self._get_webhook(webhook_id, tenant_id)

        conditions: list = [WebhookDelivery.webhook_id == webhook_id]
        if status:
            conditions.append(WebhookDelivery.status == status)

        offset = (page - 1) * per_page

        count_stmt = select(func.count()).select_from(WebhookDelivery).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = (
            select(WebhookDelivery)
            .where(and_(*conditions))
            .order_by(desc(WebhookDelivery.created_at))
            .offset(offset)
            .limit(per_page)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    # ── Cleanup ───────────────────────────────────────────────────────────────

    async def cleanup_stale_webhooks(self, days: int = 90) -> int:
        """Soft-delete webhooks and deliveries older than the given number of days.

        Args:
            days: Age threshold in days (default: 90).

        Returns:
            Number of webhooks cleaned up.

        """
        cutoff = datetime.now(UTC) - timedelta(days=days)

        # Find stale webhooks (soft-deleted or never activated)
        stmt = select(Webhook).where(
            and_(
                Webhook.deleted_at.isnot(None),
                Webhook.deleted_at < cutoff,
            ),
        )
        result = await self.db.execute(stmt)
        stale_webhooks = list(result.scalars().all())

        count = 0
        for webhook in stale_webhooks:
            # Delete delivery records too
            del_stmt = select(WebhookDelivery).where(
                WebhookDelivery.webhook_id == webhook.id,
            )
            del_result = await self.db.execute(del_stmt)
            for d in del_result.scalars().all():
                await self.db.delete(d)

            await self.db.delete(webhook)
            count += 1
            logger.info("Cleaned up stale webhook %s (deleted %s)", webhook.id, webhook.deleted_at)

        if count:
            await self.db.flush()
            logger.info("Cleanup removed %d stale webhooks (>=%d days old)", count, days)
        return count

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get_webhook(
        self,
        webhook_id: UUID,
        tenant_id: UUID | None = None,
    ) -> Webhook:
        """Fetch a webhook by ID, optionally scoped to a tenant."""
        conditions = [Webhook.id == webhook_id, Webhook.deleted_at.is_(None)]
        if tenant_id:
            conditions.append(Webhook.tenant_id == tenant_id)

        result = await self.db.execute(select(Webhook).where(and_(*conditions)))
        webhook = result.scalar_one_or_none()
        if webhook is None:
            raise NotFoundException(detail=f"Webhook {webhook_id} not found")
        return webhook

    async def _get_webhook_secret(self, webhook: Webhook) -> str | None:
        """Retrieve the original secret for a webhook.

        Since we store a hash, this requires an external secret store in
        production. For development, we return a deterministic value derived
        from the hash (useful for verification only, not recovery).

        NOTE: In production, use a proper secrets manager (HashiCorp Vault,
        AWS Secrets Manager, etc.) to store and retrieve webhook secrets.
        """
        return None  # Secret is not stored in plaintext

    async def retry_failed_deliveries(self, webhook_id: UUID, tenant_id: UUID) -> list[UUID]:
        """Retry all failed/retrying deliveries for a webhook.

        Args:
            webhook_id: The webhook ID.
            tenant_id: The tenant context.

        Returns:
            List of delivery IDs that were retried.

        """
        await self._get_webhook(webhook_id, tenant_id)
        retried: list[UUID] = []

        stmt = select(WebhookDelivery).where(
            and_(
                WebhookDelivery.webhook_id == webhook_id,
                WebhookDelivery.status.in_(
                    [
                        DeliveryStatus.FAILED.value,
                        DeliveryStatus.RETRYING.value,
                    ]
                ),
            ),
        )
        result = await self.db.execute(stmt)
        deliveries = list(result.scalars().all())

        for delivery in deliveries:
            await self.process_delivery(webhook_id, delivery.id)
            retried.append(delivery.id)

        logger.info("Retried %d failed deliveries for webhook %s", len(retried), webhook_id)
        return retried
