"""
Factory classes for AI Agent models:
AIAgent, KnowledgeDocument, Conversation.
"""

from __future__ import annotations

import uuid

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.ai import AIAgent, Conversation, KnowledgeDocument


class BaseFactory(SQLAlchemyModelFactory):
    """Abstract base — defers flush to the test fixture."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class AIAgentFactory(BaseFactory):
    """Generate realistic AIAgent instances."""

    class Meta:
        model = AIAgent

    tenant_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("sentence", nb_words=3)
    slug = factory.Sequence(lambda n: f"agent-{n}")
    agent_type = factory.Iterator([
        "chatbot", "assistant", "workflow", "analyst",
    ])
    description = factory.Faker("sentence", nb_words=10)
    system_prompt = factory.Faker("paragraph", nb_sentences=6)
    configuration = factory.Dict({
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 2048,
    })
    tools = factory.List(["search_knowledge", "get_weather"])
    memory_config = factory.Dict({
        "type": "sliding_window",
        "window_size": 20,
    })
    guardrails = factory.List([
        {"type": "topic_filter", "blocked_topics": ["competitor_pricing"]},
    ])
    is_active = True
    is_public = False
    version = 1
    total_executions = 0
    avg_response_time_ms = None


class KnowledgeDocumentFactory(BaseFactory):
    """Generate realistic KnowledgeDocument instances."""

    class Meta:
        model = KnowledgeDocument

    tenant_id = factory.LazyFunction(uuid.uuid4)
    title = factory.Faker("sentence", nb_words=4)
    content = factory.Faker("paragraph", nb_sentences=10)
    doc_type = factory.Iterator([
        "article", "faq", "guide", "policy", "integration_doc",
    ])
    source = factory.Iterator([
        "manual", "import", "generated", "web_scrape",
    ])
    category = factory.Iterator([
        "product", "support", "sales", "engineering", "compliance",
    ])
    tags = factory.List(["knowledge-base", "reference"])
    metadata = factory.Dict({"author": "AI Generator", "version": "1.0"})
    embedding_id = None
    chunk_count = 5
    is_indexed = False
    version = 1


class ConversationFactory(BaseFactory):
    """Generate realistic Conversation instances."""

    class Meta:
        model = Conversation

    tenant_id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    agent_id = factory.LazyFunction(uuid.uuid4)
    title = factory.Faker("sentence", nb_words=4)
    context = factory.Dict({"page": "/help", "prior_intent": "onboarding"})
    message_count = 0
    is_archived = False
