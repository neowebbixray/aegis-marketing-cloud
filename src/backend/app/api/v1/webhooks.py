"""Webhook router: registration, delivery management, event catalog, and secret rotation.

All endpoints (except the event catalog) require an authenticated active user and
tenant context.  Responses use the standard ``{data, meta, links}`` envelope for
lists and ``{data: {...}}`` for single resources.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.auth import User
from app.schemas.base import build_list_response, build_single_response
from app.schemas.webhooks import (
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookEventCatalogResponse,
    WebhookEventType,
    WebhookResponse,
    WebhookSecretRotateResponse,
    WebhookTestResponse,
    WebhookUpdate,
)
from app.services.webhooks import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ── Event Catalog ─────────────────────────────────────────────────────────────


@router.get("/events", name="webhook_event_catalog")
async def list_event_catalog() -> dict:
    """Get the webhook event catalog — all supported event types with schemas.

    This is a public endpoint (no auth required) per the API spec.
    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    catalog = WebhookService.get_event_catalog()
    items = [
        WebhookEventCatalogResponse(
            event_type=event_type,
            **metadata,
        ).model_dump()
        for event_type, metadata in catalog.items()
    ]
    return build_single_response(items)


@router.get("/events/{event_type}", name="webhook_event_detail")
async def get_event_detail(event_type: str) -> dict:
    """Get details for a specific event type.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    catalog = WebhookService.get_event_catalog()
    meta = catalog.get(event_type)
    if meta is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown event type '{event_type}'. See GET /webhooks/events for valid types.",
        )
    item = WebhookEventCatalogResponse(
        event_type=event_type,
        **meta,
    ).model_dump()
    return build_single_response(item)


# ── CRUD ──────────────────────────────────────────────────────────────────────


@router.post("", status_code=201, name="webhook_create")
async def create_webhook(
    body: WebhookCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new webhook endpoint.

    The request must specify at least one event type from the event catalog.
    A signing secret can be provided for HMAC-SHA256 signature verification.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request)
    service = WebhookService(db)
    webhook = await service.create_webhook(
        tenant_id=tenant_id,
        url=body.url,
        events=[e.value for e in body.events],
        secret=body.secret,
        api_version=body.api_version,
        retry_config=body.retry_config.model_dump() if body.retry_config else None,
        description=body.description,
        is_active=body.is_active,
    )
    return build_single_response(WebhookResponse.model_validate(webhook))


@router.get("", name="webhook_list")
async def list_webhooks(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    is_active: bool | None = Query(None),
    event_type: str | None = Query(None, max_length=100),
) -> dict:
    """List webhook endpoints for the current tenant.

    Optionally filter by ``is_active`` status or ``event_type``.
    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request)
    service = WebhookService(db)
    items, total = await service.list_webhooks(
        tenant_id=tenant_id,
        is_active=is_active,
        event_type=event_type,
        page=page,
        per_page=per_page,
    )
    return build_list_response(
        data=[WebhookResponse.model_validate(w) for w in items],
        total=total,
        page=page,
        per_page=per_page,
        request=request,
    )


@router.get("/{webhook_id}", name="webhook_detail")
async def get_webhook(
    webhook_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get details for a single webhook.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request)
    service = WebhookService(db)
    webhook = await service.get_webhook(webhook_id, tenant_id)
    return build_single_response(WebhookResponse.model_validate(webhook))


@router.patch("/{webhook_id}", name="webhook_update")
async def update_webhook(
    webhook_id: UUID,
    body: WebhookUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a webhook — e.g. change URL, events, or deactivate.

    Only provided fields are updated. Returns the docs-mandated
    ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request)
    service = WebhookService(db)

    updates: dict[str, Any] = {}
    if body.url is not None:
        updates["url"] = body.url
    if body.events is not None:
        updates["events"] = [e.value for e in body.events]
    if body.description is not None:
        updates["description"] = body.description
    if body.is_active is not None:
        updates["is_active"] = body.is_active
    if body.api_version is not None:
        updates["api_version"] = body.api_version
    if body.retry_config is not None:
        updates["retry_config"] = body.retry_config.model_dump()

    webhook = await service.update_webhook(webhook_id, tenant_id, **updates)
    return build_single_response(WebhookResponse.model_validate(webhook))


@router.delete("/{webhook_id}", status_code=204, name="webhook_delete")
async def delete_webhook(
    webhook_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a webhook endpoint.

    Returns 204 No Content on success.
    """
    tenant_id = await get_tenant_context(request)
    service = WebhookService(db)
    await service.delete_webhook(webhook_id, tenant_id)


# ── Test Event ────────────────────────────────────────────────────────────────


@router.post("/{webhook_id}/test", name="webhook_test")
async def send_test_event(
    webhook_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a test event to the webhook to verify connectivity.

    Creates a ``webhook.test`` delivery and dispatches it immediately.
    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request)
    service = WebhookService(db)
    payload = {
        "message": "This is a test event from Aegis Marketing Cloud.",
        "timestamp": str(request.headers.get("date", "")),
        "webhook_id": str(webhook_id),
    }
    delivery_ids = await service.dispatch_event(
        event_type=WebhookEventType.WEBHOOK_TEST.value,
        tenant_id=tenant_id,
        payload=payload,
    )
    if not delivery_ids:
        raise HTTPException(
            status_code=400,
            detail="Webhook is not active or not subscribed to test events. "
            "Ensure the webhook is active and subscribed to 'webhook.test'.",
        )
    return build_single_response(
        WebhookTestResponse(
            delivery_id=delivery_ids[0],
            status="sent",
        ).model_dump(),
    )


# ── Secret Rotation ────────────────────────────────────────────────────────────


@router.post("/{webhook_id}/rotate-secret", name="webhook_rotate_secret")
async def rotate_secret(
    webhook_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Rotate the signing secret for a webhook.

    The new secret is returned in the response and shown exactly once.
    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request)
    service = WebhookService(db)
    result = await service.rotate_secret(webhook_id, tenant_id)
    return build_single_response(
        WebhookSecretRotateResponse(
            id=webhook_id,
            message="Secret rotated successfully. The new secret is shown once.",
        ).model_dump()
        | {"secret": result["secret"]},
    )


# ── Delivery Logs ──────────────────────────────────────────────────────────────


@router.get("/{webhook_id}/deliveries", name="webhook_delivery_logs")
async def list_deliveries(
    webhook_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    status: str | None = Query(None, max_length=20),
) -> dict:
    """Get delivery history for a webhook.

    Optionally filter by ``status`` (e.g. ``succeeded``, ``failed``, ``retrying``).
    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request)
    service = WebhookService(db)
    items, total = await service.get_delivery_logs(
        webhook_id=webhook_id,
        tenant_id=tenant_id,
        page=page,
        per_page=per_page,
        status=status,
    )
    return build_list_response(
        data=[WebhookDeliveryResponse.model_validate(d) for d in items],
        total=total,
        page=page,
        per_page=per_page,
        request=request,
    )


@router.get("/{webhook_id}/deliveries/{delivery_id}", name="webhook_delivery_detail")
async def get_delivery_detail(
    webhook_id: UUID,
    delivery_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get details for a specific delivery attempt.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request)
    service = WebhookService(db)
    # Verify webhook belongs to tenant
    await service.get_webhook(webhook_id, tenant_id)
    # Fetch delivery
    items, _total = await service.get_delivery_logs(
        webhook_id=webhook_id,
        tenant_id=tenant_id,
        page=1,
        per_page=1,
    )
    delivery = None
    for d in items:
        if d.id == delivery_id:
            delivery = d
            break
    if delivery is None:
        raise HTTPException(
            status_code=404,
            detail=f"Delivery {delivery_id} not found for webhook {webhook_id}",
        )
    return build_single_response(WebhookDeliveryResponse.model_validate(delivery))


# ── Retry ──────────────────────────────────────────────────────────────────────


@router.post(
    "/{webhook_id}/redeliver/{delivery_id}",
    name="webhook_redeliver",
)
async def redeliver_webhook(
    webhook_id: UUID,
    delivery_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retry a failed or retrying webhook delivery.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    await get_tenant_context(request)
    service = WebhookService(db)
    delivery = await service.process_delivery(webhook_id, delivery_id)
    return build_single_response(WebhookDeliveryResponse.model_validate(delivery))
