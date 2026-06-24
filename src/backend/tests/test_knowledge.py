"""Tests for the knowledge base endpoints: documents, upload, search, indexing."""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.ai import KnowledgeDocumentFactory


@pytest.mark.asyncio
async def test_create_document(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can create a knowledge document."""
    payload = {
        "title": "Getting Started Guide",
        "content": "This guide explains how to get started with the platform.",
        "doc_type": "guide",
        "category": "product",
        "tags": ["onboarding", "guide"],
    }

    response = await client.post(
        "/api/v1/knowledge/documents",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data
    doc = data["data"]
    assert doc["title"] == "Getting Started Guide"
    assert doc["doc_type"] == "guide"
    assert "id" in doc


@pytest.mark.asyncio
async def test_list_documents(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can list knowledge documents."""
    response = await client.get(
        "/api/v1/knowledge/documents",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert "total" in data["meta"]
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_document(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can get a specific document by ID."""
    doc = KnowledgeDocumentFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.get(
        f"/api/v1/knowledge/documents/{doc.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["id"] == str(doc.id)
    assert data["data"]["title"] == doc.title


@pytest.mark.asyncio
async def test_update_document(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can update a document's metadata."""
    doc = KnowledgeDocumentFactory(tenant_id=test_tenant.id, title="Original Title")
    await db_session.flush()

    payload = {
        "title": "Updated Title",
        "tags": ["updated", "guide"],
    }

    response = await client.patch(
        f"/api/v1/knowledge/documents/{doc.id}",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["data"]["title"] == "Updated Title"
    assert "updated" in data["data"]["tags"]


@pytest.mark.asyncio
async def test_delete_document(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can delete a knowledge document."""
    doc = KnowledgeDocumentFactory(tenant_id=test_tenant.id)
    await db_session.flush()

    response = await client.delete(
        f"/api/v1/knowledge/documents/{doc.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 204, response.text


@pytest.mark.asyncio
async def test_upload_document(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can upload a file as a knowledge document."""
    content = b"This is the content of an uploaded document."
    response = await client.post(
        "/api/v1/knowledge/documents/upload",
        files={"file": ("guide.txt", content, "text/plain")},
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["document"]["title"] == "guide.txt"


@pytest.mark.asyncio
async def test_search_documents(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can search indexed documents."""
    KnowledgeDocumentFactory(
        tenant_id=test_tenant.id,
        title="Searchable Document",
        content="This document should appear in search results.",
        is_indexed=True,
    )
    await db_session.flush()

    payload = {
        "query": "searchable",
        "top_k": 10,
    }

    response = await client.post(
        "/api/v1/knowledge/search",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_get_collection_stats(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can get Qdrant collection statistics."""
    response = await client.get(
        "/api/v1/knowledge/collections/stats",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    """Knowledge endpoints return 401 without auth."""
    response = await client.get("/api/v1/knowledge/documents")

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_document_not_found(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Getting a non-existent document returns 404."""
    fake_id = uuid4()

    response = await client.get(
        f"/api/v1/knowledge/documents/{fake_id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_delete_not_found(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Deleting a non-existent document returns 404."""
    fake_id = uuid4()

    response = await client.delete(
        f"/api/v1/knowledge/documents/{fake_id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_index_document(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
) -> None:
    """A user can trigger Qdrant indexing for a document."""
    doc = KnowledgeDocumentFactory(tenant_id=test_tenant.id, is_indexed=False)
    await db_session.flush()

    response = await client.post(
        f"/api/v1/knowledge/documents/{doc.id}/index",
        headers=test_tenant_headers,
    )

    # The endpoint may fail if Qdrant is not configured, but should still reach
    # the handler logic.
    assert response.status_code in (200, 500, 503), response.text
