"""Tests for health check endpoints: liveness, readiness, and full health report."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness(client: AsyncClient) -> None:
    """The liveness endpoint returns 200 with status 'alive'."""
    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "alive"
    assert "app" in data


@pytest.mark.asyncio
async def test_readiness(client: AsyncClient) -> None:
    """The readiness endpoint returns 200 with status 'ready' or degraded."""
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] in ("ready", "not_ready")
    assert "database" in data


@pytest.mark.asyncio
async def test_full_health(client: AsyncClient) -> None:
    """The full health endpoint returns a structured report with services."""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] in ("healthy", "degraded", "unhealthy")
    assert "app" in data
    assert "version" in data
    assert "environment" in data
    assert "services" in data
    assert isinstance(data["services"], list)


@pytest.mark.asyncio
async def test_full_health_contains_postgres_check(client: AsyncClient) -> None:
    """The full health report includes a postgres service check."""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    data = response.json()
    service_names = [s["name"] for s in data["services"]]
    assert "postgres" in service_names


@pytest.mark.asyncio
async def test_legacy_health(client: AsyncClient) -> None:
    """The legacy health endpoint is still accessible."""
    response = await client.get("/api/v1/health/legacy")

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert "database" in data
    assert "version" in data
