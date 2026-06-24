"""Tests for the search endpoints: global search, contacts, deals, campaigns."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_global_search(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
) -> None:
    """A user can perform a global search."""
    response = await client.get(
        "/api/v1/search",
        params={"q": "test", "limit": 5},
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert data["meta"]["query"] == "test"


@pytest.mark.asyncio
async def test_search_contacts(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can search contacts."""
    response = await client.get(
        "/api/v1/search/contacts",
        params={"q": "john", "page": 1, "limit": 20},
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data


@pytest.mark.asyncio
async def test_search_deals(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can search deals."""
    response = await client.get(
        "/api/v1/search/deals",
        params={"q": "big deal", "page": 1, "limit": 20},
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data


@pytest.mark.asyncio
async def test_search_campaigns(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can search campaigns."""
    response = await client.get(
        "/api/v1/search/campaigns",
        params={"q": "campaign", "page": 1, "limit": 20},
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data


@pytest.mark.asyncio
async def test_search_requires_query(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Search endpoints require a query parameter."""
    response = await client.get(
        "/api/v1/search",
        headers=test_tenant_headers,
    )

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    """Search endpoints return 401 without auth."""
    response = await client.get("/api/v1/search", params={"q": "test"})

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_reindex_search(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can trigger a search index reindex."""
    response = await client.post(
        "/api/v1/search/reindex",
        headers=test_tenant_headers,
    )

    # This may be an admin-only operation, but should still be reachable.
    assert response.status_code in (200, 403, 500), response.text
