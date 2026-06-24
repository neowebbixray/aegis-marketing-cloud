"""Tests for the analytics endpoints: events, metrics, dashboards, reports."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.analytics import (
    AnalyticsDashboardFactory,
    MetricSnapshotFactory,
)


@pytest.mark.asyncio
async def test_track_event(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can track an analytics event."""
    payload = {
        "event_name": "page_view",
        "properties": {"url": "https://example.com/home", "referrer": "https://google.com"},
        "entity_type": "campaign",
        "session_id": "sess-test123",
    }

    response = await client.post(
        "/api/v1/analytics/events",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["event_name"] == "page_view"
    assert "id" in data["data"]


@pytest.mark.asyncio
async def test_track_events_batch(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can track multiple events in a batch."""
    payload = [
        {
            "event_name": "page_view",
            "properties": {"url": "/home"},
            "session_id": "sess-1",
        },
        {
            "event_name": "click",
            "properties": {"url": "/pricing"},
            "session_id": "sess-1",
        },
    ]

    response = await client.post(
        "/api/v1/analytics/events/batch",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["ingested"] == 2


@pytest.mark.asyncio
async def test_query_metrics(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can query aggregated metrics."""
    MetricSnapshotFactory(
        tenant_id=test_tenant.id,
        metric_name="page_views",
        value=100,
    )
    await db_session.flush()

    response = await client.get(
        "/api/v1/analytics/metrics/query",
        params={"metric_names": "page_views", "granularity": "day"},
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_get_active_users(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can get active user counts."""
    response = await client.get(
        "/api/v1/analytics/metrics/active-users",
        params={"period": 7},
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_get_events_summary(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can get event count summaries."""
    response = await client.get(
        "/api/v1/analytics/metrics/events-summary",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_create_dashboard(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can create a dashboard."""
    payload = {
        "title": "Marketing KPIs",
        "description": "Main marketing dashboard",
        "widgets": [
            {
                "type": "line_chart",
                "title": "Page Views",
                "config": {"metric": "page_views"},
                "position": {"x": 0, "y": 0, "w": 6, "h": 4},
            },
        ],
    }

    response = await client.post(
        "/api/v1/analytics/dashboards",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["title"] == "Marketing KPIs"


@pytest.mark.asyncio
async def test_list_dashboards(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can list dashboards."""
    response = await client.get(
        "/api/v1/analytics/dashboards",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data


@pytest.mark.asyncio
async def test_get_dashboard(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can get a specific dashboard by ID."""
    dash = AnalyticsDashboardFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/analytics/dashboards/{dash.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["id"] == str(dash.id)


@pytest.mark.asyncio
async def test_update_dashboard(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can update a dashboard."""
    dash = AnalyticsDashboardFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    payload = {
        "title": "Updated Dashboard Title",
        "description": "Updated description",
    }

    response = await client.patch(
        f"/api/v1/analytics/dashboards/{dash.id}",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["data"]["title"] == "Updated Dashboard Title"


@pytest.mark.asyncio
async def test_delete_dashboard(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can delete a dashboard."""
    dash = AnalyticsDashboardFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.delete(
        f"/api/v1/analytics/dashboards/{dash.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 204, response.text


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    """Analytics endpoints return 401 without auth."""
    response = await client.get("/api/v1/analytics/dashboards")

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_dashboard_not_found(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Getting a non-existent dashboard returns 404."""
    fake_id = uuid4()

    response = await client.get(
        f"/api/v1/analytics/dashboards/{fake_id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 404, response.text
