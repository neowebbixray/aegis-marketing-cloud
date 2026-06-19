"""AI Agent models — agents, executions, knowledge, conversations, messages.

Tenant-scoped: AI agents and knowledge are shared within a tenant.
Conversations are workspace-scoped.
"""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class AIAgent(BaseModel):
    """AI Agent definition — type, prompt, tools, memory config."""

    __tablename__ = "ai_agents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    agent_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    tools: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    memory_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    guardrails: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    total_executions: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<AIAgent {self.name} ({self.agent_type})>"


class AIAgentExecution(BaseModel):
    """Record of a single AI agent execution."""

    __tablename__ = "ai_agent_executions"

    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("ai_agents.id", ondelete="CASCADE"), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    tool_calls: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<AIAgentExecution {self.agent_id} ({self.status})>"


class KnowledgeDocument(BaseModel):
    """Knowledge document indexed for RAG / agent context."""

    __tablename__ = "knowledge_documents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tags: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    meta_data: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)
    embedding_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunk_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)

    def __repr__(self) -> str:
        return f"<KnowledgeDocument {self.title}>"


class Conversation(BaseModel):
    """Conversation thread between a user and an AI agent."""

    __tablename__ = "conversations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("ai_agents.id", ondelete="SET NULL"), nullable=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    context: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=dict)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Conversation {self.title or self.id}>"


class Message(BaseModel):
    """Individual message within a conversation."""

    __tablename__ = "messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_calls: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    tool_call_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    meta_data: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB, nullable=True, default=dict)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

    def __repr__(self) -> str:
        return f"<Message {self.role}:{len(self.content)}>"
