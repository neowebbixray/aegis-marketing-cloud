"""
Tests for the media endpoints: upload, list, detail, update, delete.
"""

from __future__ import annotations

from io import BytesIO
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.media import MediaAssetFactory


@pytest.mark.asyncio
async def test_upload_media(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can upload a media file."""
    file_content = b"fake-image-content"
    response = await client.post(
        "/api/v1/media/upload",
        files={"file": ("test.png", BytesIO(file_content), "image/png")},
        data={"category": "images", "alt_text": "Test image", "is_public": False},
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data
    asset = data["data"]
    assert "id" in asset
    assert asset["original_filename"] == "test.png"
    assert asset["mime_type"] == "image/png"
    assert asset["category"] == "images"
    assert asset["alt_text"] == "Test image"


@pytest.mark.asyncio
async def test_upload_multiple_media(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can upload multiple media files."""
    file1 = ("file1.png", BytesIO(b"content1"), "image/png")
    file2 = ("file2.pdf", BytesIO(b"content2"), "application/pdf")

    response = await client.post(
        "/api/v1/media/upload-multiple",
        files=[
            ("files", file1),
            ("files", file2),
        ],
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data
    assert len(data["data"]) == 2


@pytest.mark.asyncio
async def test_list_media(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can list media assets."""
    response = await client.get(
        "/api/v1/media",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert "total" in data["meta"]
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_media(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can get a specific media asset by ID."""
    asset = MediaAssetFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/media/{asset.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["id"] == str(asset.id)
    assert data["data"]["original_filename"] == asset.original_filename


@pytest.mark.asyncio
async def test_update_media(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can update a media asset's metadata."""
    asset = MediaAssetFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    payload = {
        "alt_text": "Updated alt text",
        "is_public": True,
    }

    response = await client.patch(
        f"/api/v1/media/{asset.id}",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["data"]["alt_text"] == "Updated alt text"
    assert data["data"]["is_public"] is True


@pytest.mark.asyncio
async def test_delete_media(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can delete a media asset."""
    asset = MediaAssetFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.delete(
        f"/api/v1/media/{asset.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 204, response.text


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    """Media endpoints return 401 without auth."""
    response = await client.get("/api/v1/media")

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_media_not_found(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Getting a non-existent media asset returns 404."""
    fake_id = uuid4()

    response = await client.get(
        f"/api/v1/media/{fake_id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_delete_not_found(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Deleting a non-existent media asset returns 404."""
    fake_id = uuid4()

    response = await client.delete(
        f"/api/v1/media/{fake_id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 404, response.text
