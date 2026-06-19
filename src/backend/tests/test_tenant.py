"""
Tests for the tenant and workspace endpoints.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_workspace(client: AsyncClient, auth_headers, sample_tenant) -> None:
    """An authenticated user can create a workspace."""
    payload = {
        "name": "New Workspace",
        "slug": "new-workspace",
    }
    headers = auth_headers.copy()
    headers["X-Tenant-ID"] = str(sample_tenant.id)

    response = await client.post(
        "/api/v1/tenants/workspaces",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["name"] == "New Workspace"
    assert data["slug"] == "new-workspace"
    assert data["is_default"] is False


@pytest.mark.asyncio
async def test_list_workspaces(client: AsyncClient, auth_headers, sample_tenant, sample_workspace) -> None:
    """A user can list workspaces in their tenant."""
    headers = auth_headers.copy()
    headers["X-Tenant-ID"] = str(sample_tenant.id)

    response = await client.get(
        "/api/v1/tenants/workspaces",
        headers=headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    # Check the sample workspace is present
    slugs = [w["slug"] for w in data]
    assert "test-workspace" in slugs


@pytest.mark.asyncio
async def test_invite_user(
    client: AsyncClient,
    auth_headers,
    sample_tenant,
    sample_workspace,
    sample_role,
    sample_user2,
) -> None:
    """A user with admin role can invite another user to a workspace."""
    headers = auth_headers.copy()
    headers["X-Tenant-ID"] = str(sample_tenant.id)

    payload = {
        "email": "testuser2@example.com",
        "role_id": str(sample_role.id),
    }

    response = await client.post(
        f"/api/v1/tenants/workspaces/{sample_workspace.id}/invite",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "detail" in data
    assert data["user_role_id"] is not None


@pytest.mark.asyncio
async def test_invite_nonexistent_user(
    client: AsyncClient,
    auth_headers,
    sample_tenant,
    sample_workspace,
    sample_role,
) -> None:
    """Inviting a non-existent user returns 404 (for now)."""
    headers = auth_headers.copy()
    headers["X-Tenant-ID"] = str(sample_tenant.id)

    payload = {
        "email": "nobody@example.com",
        "role_id": str(sample_role.id),
    }

    response = await client.post(
        f"/api/v1/tenants/workspaces/{sample_workspace.id}/invite",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 404, response.text
