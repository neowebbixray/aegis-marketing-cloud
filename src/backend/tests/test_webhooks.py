"""
Tests for the webhook endpoints: CRUD, deliveries, test, secret rotation.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.webhooks import WebhookDeliveryFactory, WebhookFactory


@pytest.mark.asyncio
async def test_event_catalog(client: AsyncClient) -> None:
    """The event catalog is publicly accessible."""
    response = await client.get("/api/v1/webhooks/events")

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_create_webhook(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can create a webhook."""
    payload = {
        "url": "https://example.com/webhook",
        "events": ["contact.created", "deal.updated"],
        "description": "Test webhook",
        "is_active": True,
    }

    response = await client.post(
        "/api/v1/webhooks",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data
    wh = data["data"]
    assert wh["url"] == "https://example.com/webhook"
    assert "contact.created" in wh["events"]
    assert "id" in wh


@pytest.mark.asyncio
async def test_list_webhooks(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can list webhooks."""
    response = await client.get(
        "/api/v1/webhooks",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data


@pytest.mark.asyncio
async def test_get_webhook(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can get a specific webhook by ID."""
    wh = WebhookFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/webhooks/{wh.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["id"] == str(wh.id)


@pytest.mark.asyncio
async def test_update_webhook(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can update a webhook's URL and events."""
    wh = WebhookFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    payload = {
        "url": "https://updated.example.com/webhook",
        "description": "Updated webhook",
    }

    response = await client.patch(
        f"/api/v1/webhooks/{wh.id}",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["data"]["url"] == "https://updated.example.com/webhook"
    assert data["data"]["description"] == "Updated webhook"


@pytest.mark.asyncio
async def test_delete_webhook(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can delete a webhook."""
    wh = WebhookFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.delete(
        f"/api/v1/webhooks/{wh.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 204, response.text


@pytest.mark.asyncio
async def test_rotate_secret(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can rotate a webhook's signing secret."""
    wh = WebhookFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/webhooks/{wh.id}/rotate-secret",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    """Webhook endpoints return 401 without auth."""
    response = await client.get("/api/v1/webhooks")

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_webhook_not_found(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Getting a non-existent webhook returns 404."""
    fake_id = uuid4()

    response = await client.get(
        f"/api/v1/webhooks/{fake_id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_delete_not_found(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Deleting a non-existent webhook returns 404."""
    fake_id = uuid4()

    response = await client.delete(
        f"/api/v1/webhooks/{fake_id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 404, response.text
