"""
Celery task for async webhook delivery with exponential backoff retry.

Requires Celery to be installed and configured (``pip install celery[redis]``).

Usage:
    In production, start a Celery worker:
        ``celery -A app.tasks.webhook_delivery worker -l info``

    Dispatch from anywhere:
        ``from app.tasks.webhook_delivery import deliver_webhook
        deliver_webhook.delay(webhook_id, delivery_id, url, payload, event_type, secret)``

Gracefully falls back when Celery is not installed.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import random
import time
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger("amc.tasks.webhook_delivery")

# ── Constants ─────────────────────────────────────────────────────────────────

SIGNATURE_HEADER = "X-Webhook-Signature"
SIGNATURE_VERSION = "v1"
DELIVERY_TIMEOUT = 30  # seconds
MAX_RETRIES_DEFAULT = 5


# ── Helpers ───────────────────────────────────────────────────────────────────


def _compute_signature(payload: str, secret: str) -> str:
    """Compute HMAC-SHA256 signature for the given payload and secret."""
    mac = hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    )
    return f"{SIGNATURE_VERSION},{mac.hexdigest()}"


def _build_headers(
    webhook_id: str,
    delivery_id: str,
    event_type: str,
    attempt: int,
    secret: str | None = None,
) -> dict[str, str]:
    """Build standard webhook delivery headers."""
    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": "Aegis-Webhook/1.0",
        "X-Webhook-ID": webhook_id,
        "X-Webhook-Event": event_type,
        "X-Webhook-Delivery-ID": delivery_id,
        "X-Webhook-Attempt": str(attempt),
    }
    return headers


def _calculate_retry_delay(attempt: int) -> int:
    """Calculate exponential backoff delay (seconds) for Celery retry."""
    base = 60  # 1 minute
    delay = base * (2 ** (attempt - 1))
    jitter = random.randint(0, min(delay // 2, 300))  # up to 50% jitter, max 5 min
    return min(delay + jitter, 3600)  # cap at 1 hour


# ── Celery task (optional dependency) ─────────────────────────────────────────

try:
    from celery import Celery  # noqa: F811
    from celery.exceptions import MaxRetriesExceededError  # noqa: F811

    celery_app = Celery(
        "webhook_delivery",
        broker=settings.celery_broker_url or "redis://localhost:6379/0",
    )

    @celery_app.task(
        bind=True,
        max_retries=MAX_RETRIES_DEFAULT,
        default_retry_delay=60,
        autoretry_for=(httpx.RequestError, httpx.TimeoutException),
        retry_backoff=True,
        retry_backoff_max=3600,
        retry_jitter=True,
        name="webhook.deliver",
    )
    def deliver_webhook(
        self,
        webhook_id: str,
        delivery_id: str,
        url: str,
        payload: dict[str, Any],
        event_type: str,
        secret: str | None = None,
        retry_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Deliver a webhook event to a subscriber endpoint with retry.

        This task is called by the Celery worker.  It performs an HTTP POST
        to the webhook URL with the event payload and signs the request if
        a secret is provided.

        Args:
            webhook_id: UUID of the webhook registration.
            delivery_id: UUID of the delivery record.
            url: Target URL to POST to.
            payload: Event payload dict.
            event_type: The event type string.
            secret: Optional signing secret.
            retry_config: Optional retry configuration overrides.

        Returns:
            Dict with delivery result metadata.

        Raises:
            MaxRetriesExceededError: If all retry attempts are exhausted.
        """
        attempt = self.request.retries + 1
        payload_str = json.dumps(payload, default=str)

        headers = _build_headers(
            webhook_id=webhook_id,
            delivery_id=delivery_id,
            event_type=event_type,
            attempt=attempt,
            secret=secret,
        )

        if secret:
            headers[SIGNATURE_HEADER] = _compute_signature(payload_str, secret)

        logger.info(
            "Delivering webhook %s delivery %s (attempt %d/%d) to %s",
            webhook_id,
            delivery_id,
            attempt,
            self.max_retries or MAX_RETRIES_DEFAULT,
            url,
        )

        start = time.monotonic()
        try:
            with httpx.Client(timeout=DELIVERY_TIMEOUT) as client:
                response = client.post(url, content=payload_str, headers=headers)
            duration_ms = int((time.monotonic() - start) * 1000)

            if 200 <= response.status_code < 300:
                logger.info(
                    "Webhook delivery %s succeeded (%d) in %dms",
                    delivery_id,
                    response.status_code,
                    duration_ms,
                )
                return {
                    "status": "succeeded",
                    "delivery_id": delivery_id,
                    "response_status": response.status_code,
                    "duration_ms": duration_ms,
                    "attempt": attempt,
                }
            else:
                logger.warning(
                    "Webhook delivery %s returned %d (attempt %d)",
                    delivery_id,
                    response.status_code,
                    attempt,
                )
                # Retry for non-2xx responses
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response,
                )

        except (httpx.RequestError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            duration_ms = int((time.monotonic() - start) * 1000)

            if attempt >= MAX_RETRIES_DEFAULT:
                logger.error(
                    "Webhook delivery %s failed permanently after %d attempts",
                    delivery_id,
                    attempt,
                )
                raise

            retry_delay = _calculate_retry_delay(attempt)
            logger.info(
                "Webhook delivery %s will retry in %ds (attempt %d)",
                delivery_id,
                retry_delay,
                attempt,
            )

            # Re-raise to trigger Celery auto-retry
            raise self.retry(exc=exc, countdown=retry_delay)

        except Exception as exc:
            logger.exception(
                "Unexpected error delivering webhook %s: %s", delivery_id, exc
            )
            raise

except ImportError:
    # Celery not installed — provide a stub fallback
    def deliver_webhook(*args: Any, **kwargs: Any) -> dict[str, Any]:  # type: ignore[misc]
        """Fallback when Celery is not installed."""
        logger.warning(
            "Celery is not installed. Cannot deliver webhook asynchronously. "
            "Install it with: pip install celery[redis]"
        )
        return {
            "status": "error",
            "detail": "Celery not available. Install celery[redis] to use async delivery.",
        }
