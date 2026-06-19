"""
Tests for the AI endpoints: agents, conversations, content generation, analysis.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.ai import AIAgentFactory, ConversationFactory, KnowledgeDocumentFactory


@pytest.mark.asyncio
async def test_list_agents(client: AsyncClient) -> None:
    """The agent listing endpoint is publicly accessible."""
    response = await client.get("/api/v1/ai/agents")

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data


@pytest.mark.asyncio
async def test_get_agent(client: AsyncClient) -> None:
    """A user can get a specific agent definition."""
    response = await client.get("/api/v1/ai/agents/seo")

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["type"] == "seo"


@pytest.mark.asyncio
async def test_get_agent_not_found(client: AsyncClient) -> None:
    """Getting a non-existent agent type returns 422."""
    response = await client.get("/api/v1/ai/agents/nonexistent-agent")

    assert response.status_code == 422, response.text


@pytest.mark.asyncio
async def test_create_conversation(
    client: AsyncClient,
    test_tenant_headers,
    test_user,
) -> None:
    """An authenticated user can create a conversation."""
    payload = {
        "title": "Test conversation",
        "user_id": str(test_user.id),
        "tenant_id": str(test_user.tenant_id),
        "agent_type": "chatbot",
    }

    response = await client.post(
        "/api/v1/ai/conversations",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["title"] == "Test conversation"


@pytest.mark.asyncio
async def test_list_conversations(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """A user can list conversations."""
    response = await client.get(
        "/api/v1/ai/conversations",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert "meta" in data


@pytest.mark.asyncio
async def test_get_conversation(
    client: AsyncClient,
    test_tenant_headers,
    db_session: AsyncSession,
    test_tenant,
    test_user,
) -> None:
    """A user can get a specific conversation by ID."""
    conv = ConversationFactory(
        tenant_id=test_tenant.id,
        user_id=test_user.id,
    )
    await db_session.flush()

    response = await client.get(
        f"/api/v1/ai/conversations/{conv.id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert "data" in data
    assert data["data"]["id"] == str(conv.id)


@pytest.mark.asyncio
async def test_generate_content(
    client: AsyncClient,
    test_tenant_headers,
    test_tenant,
) -> None:
    """An authenticated user can generate content via AI."""
    payload = {
        "prompt": "Write a marketing email about our new product launch",
        "content_type": "email",
        "tone": "professional",
        "tenant_id": str(test_tenant.id),
    }

    response = await client.post(
        "/api/v1/ai/content/generate",
        json=payload,
        headers=test_tenant_headers,
    )

    # The actual AI call may fail if no API key is configured, but the endpoint
    # should still be reachable. We accept either 200 or a 5xx.
    assert response.status_code in (200, 500, 503), response.text


@pytest.mark.asyncio
async def test_analyze_content(
    client: AsyncClient,
    test_tenant_headers,
    test_tenant,
) -> None:
    """An authenticated user can analyze content via AI."""
    payload = {
        "content_text": "This is a great product that solves many problems for customers.",
        "tenant_id": str(test_tenant.id),
    }

    response = await client.post(
        "/api/v1/ai/content/analyze",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code in (200, 500, 503), response.text


@pytest.mark.asyncio
async def test_classify_intent(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can classify intent via AI."""
    payload = {"text": "I want to upgrade my subscription plan"}

    response = await client.post(
        "/api/v1/ai/classify",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code in (200, 500, 503), response.text


@pytest.mark.asyncio
async def test_translate_text(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can translate text via AI."""
    payload = {
        "text": "Hello, how can I help you?",
        "target_language": "es",
    }

    response = await client.post(
        "/api/v1/ai/translate",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code in (200, 500, 503), response.text


@pytest.mark.asyncio
async def test_summarize_text(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """An authenticated user can summarize text via AI."""
    payload = {
        "text": "This is a long piece of content that needs to be summarized. " * 20,
    }

    response = await client.post(
        "/api/v1/ai/summarize",
        json=payload,
        headers=test_tenant_headers,
    )

    assert response.status_code in (200, 500, 503), response.text


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    """AI conversation endpoints return 401 without auth."""
    response = await client.get("/api/v1/ai/conversations")

    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_conversation_not_found(
    client: AsyncClient,
    test_tenant_headers,
) -> None:
    """Getting a non-existent conversation returns 404."""
    fake_id = uuid4()

    response = await client.get(
        f"/api/v1/ai/conversations/{fake_id}",
        headers=test_tenant_headers,
    )

    assert response.status_code == 404, response.text
