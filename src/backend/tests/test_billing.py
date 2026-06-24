"""Tests for the billing endpoints: subscriptions, invoices, wallet, usage."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.billing import (
    CreditWalletFactory,
    InvoiceFactory,
    SubscriptionFactory,
    UsageRecordFactory,
)


@pytest.mark.asyncio
async def test_create_subscription(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can create a subscription."""
    payload = {
        "plan_tier": "professional",
        "trial_days": 14,
    }

    response = await client.post(
        "/api/v1/billing/subscriptions",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data
    sub = data["data"]
    assert sub["plan_id"] == "professional"
    assert sub["status"] == "active"
    assert "id" in sub
    assert "tenant_id" in sub


@pytest.mark.asyncio
async def test_list_subscriptions(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can list subscriptions."""
    response = await client.get(
        "/api/v1/billing/subscriptions",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert "total" in data["meta"]


@pytest.mark.asyncio
async def test_get_subscription(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can get a specific subscription by ID."""
    sub = SubscriptionFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/billing/subscriptions/{sub.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["id"] == str(sub.id)


@pytest.mark.asyncio
async def test_update_subscription_plan(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can upgrade/downgrade a subscription plan."""
    sub = SubscriptionFactory(tenant_id=test_tenant.id, plan_id="starter")
    await db_session.flush()

    payload = {"plan_tier": "professional"}

    response = await client.patch(
        f"/api/v1/billing/subscriptions/{sub.id}",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["data"]["plan_id"] == "professional"


@pytest.mark.asyncio
async def test_cancel_subscription(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can cancel a subscription."""
    sub = SubscriptionFactory(tenant_id=test_tenant.id, status="active")
    await db_session.flush()

    payload = {"immediate": True}

    response = await client.post(
        f"/api/v1/billing/subscriptions/{sub.id}/cancel",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["data"]["status"] == "canceled"


@pytest.mark.asyncio
async def test_list_invoices(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can list invoices."""
    response = await client.get(
        "/api/v1/billing/invoices",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data


@pytest.mark.asyncio
async def test_get_invoice(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can get a specific invoice by ID."""
    inv = InvoiceFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/billing/invoices/{inv.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["id"] == str(inv.id)


@pytest.mark.asyncio
async def test_get_wallet(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can get wallet balance."""
    response = await client.get(
        "/api/v1/billing/wallet",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_top_up_wallet(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can top up the credit wallet."""
    CreditWalletFactory(tenant_id=test_tenant.id, balance=0)
    await db_session.flush()

    payload = {
        "amount": 100.00,
        "payment_method": "card",
    }

    response = await client.post(
        "/api/v1/billing/wallet/top-up",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_get_usage_summary(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can get usage summary."""
    sub = SubscriptionFactory(tenant_id=test_tenant.id, status="active")
    await db_session.flush()
    UsageRecordFactory(subscription_id=sub.id, metric="api_calls", quantity=10)
    await db_session.flush()

    response = await client.get(
        "/api/v1/billing/usage",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    """Billing endpoints return 401 without auth."""
    response = await client.get("/api/v1/billing/subscriptions")

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_subscription_not_found(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Getting a non-existent subscription returns 404."""
    fake_id = uuid4()

    response = await client.get(
        f"/api/v1/billing/subscriptions/{fake_id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_invoice_not_found(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Getting a non-existent invoice returns 404."""
    fake_id = uuid4()

    response = await client.get(
        f"/api/v1/billing/invoices/{fake_id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_invalid_plan_tier(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Creating a subscription with an invalid plan tier returns 422."""
    payload = {"plan_tier": "ultra-premium"}

    response = await client.post(
        "/api/v1/billing/subscriptions",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 422, response.text
