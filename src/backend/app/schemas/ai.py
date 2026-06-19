"""
Pydantic schemas for the AI module: agents, conversations, content generation,
classification, translation, summarisation, and execution history.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ── Agent Definitions ──────────────────────────────────────────────────────────

class AgentDefinition(BaseModel):
    """Definition of a single AI agent type (built-in catalog entry)."""

    type: str
    name: str
    description: str
    system_prompt: str
    default_tools: list[str]


class AgentListResponse(BaseModel):
    """List of all available agent definitions."""

    agents: list[AgentDefinition]
    total: int


# ── Agent Execution ────────────────────────────────────────────────────────────

class AgentExecuteRequest(BaseModel):
    """Payload for POST /ai/agents/{agent_type}/execute."""

    input_data: dict[str, Any] = Field(..., description="Input payload for the agent")
    tenant_id: UUID = Field(..., description="Tenant context")
    conversation_id: Optional[UUID] = Field(None, description="Optional conversation to attach this execution to")
    user_id: Optional[UUID] = Field(None, description="User initiating the execution")


class AgentExecuteResponse(BaseModel):
    """Result of an agent execution."""

    agent_type: str
    status: str
    output: Optional[dict[str, Any]] = None
    execution_id: Optional[UUID] = None
    tokens_used: Optional[int] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None


# ── Conversations ──────────────────────────────────────────────────────────────

class MessageCreate(BaseModel):
    """Payload for posting a new message to a conversation."""

    content: str = Field(..., min_length=1, max_length=100_000)
    user_id: UUID
    tenant_id: UUID


class MessageResponse(BaseModel):
    """A single message within a conversation."""

    id: UUID
    conversation_id: UUID
    role: str
    content: str
    tool_calls: Optional[list[Any]] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationCreate(BaseModel):
    """Payload for creating a new conversation."""

    title: Optional[str] = Field(None, max_length=255)
    user_id: UUID
    tenant_id: UUID
    agent_type: Optional[str] = Field(None, description="Optional agent type to associate")


class ConversationResponse(BaseModel):
    """Conversation representation (without messages)."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    title: Optional[str] = None
    agent_id: Optional[UUID] = None
    message_count: int = 0
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    """Conversation with its messages."""

    id: UUID
    tenant_id: UUID
    user_id: UUID
    title: Optional[str] = None
    agent_id: Optional[UUID] = None
    message_count: int = 0
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    messages: list[MessageResponse] = []

    model_config = {"from_attributes": True}


# ── Content Generation ─────────────────────────────────────────────────────────

class ContentGenerateRequest(BaseModel):
    """Payload for POST /ai/content/generate."""

    tenant_id: UUID
    prompt: str = Field(..., min_length=1, max_length=50_000)
    content_type: str = Field(default="general", description="e.g. blog, social, email, ad, landing_page")
    tone: Optional[str] = Field(None, description="e.g. professional, casual, urgent, friendly")
    length: Optional[str] = Field(None, description="e.g. short, medium, long")


class ContentGenerateResponse(BaseModel):
    """Generated marketing content."""

    content: str
    content_type: str
    word_count: int
    tone: Optional[str] = None


# ── Content Analysis ───────────────────────────────────────────────────────────

class ContentAnalyzeRequest(BaseModel):
    """Payload for POST /ai/content/analyze (campaign or content analysis)."""

    tenant_id: UUID
    campaign_id: Optional[UUID] = Field(None, description="Campaign ID for campaign analysis")
    content_text: Optional[str] = Field(None, description="Raw text content to analyze")
    image_url: Optional[str] = Field(None, description="Image URL for image description generation")
    style: Optional[str] = Field(None, description="Art/visual style hint for image description")


class ContentAnalyzeResponse(BaseModel):
    """Result of AI-powered content or campaign analysis."""

    analysis: str
    analysis_type: str  # 'campaign', 'content', 'image_description'
    suggestions: Optional[list[str]] = None
    image_prompt: Optional[str] = None
    alt_text: Optional[str] = None


# ── Lead Scoring ───────────────────────────────────────────────────────────────

class LeadScoreRequest(BaseModel):
    """Payload for POST /ai/leads/score."""

    contact_id: UUID = Field(..., description="Contact/lead ID to score")
    tenant_id: UUID = Field(..., description="Tenant context")


class LeadScoreResponse(BaseModel):
    """Result of AI-powered lead scoring."""

    contact_id: UUID
    score: int = Field(..., ge=0, le=100)
    rationale: str
    tier: str = Field(default="unscored", description="hot, warm, cold, unscored")


# ── Classification ─────────────────────────────────────────────────────────────

class ClassificationRequest(BaseModel):
    """Payload for POST /ai/classify."""

    text: str = Field(..., min_length=1, max_length=50_000)


class ClassificationResponse(BaseModel):
    """Intent classification result."""

    intent: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    categories: Optional[list[dict[str, Any]]] = None


# ── Translation ────────────────────────────────────────────────────────────────

class TranslationRequest(BaseModel):
    """Payload for POST /ai/translate."""

    text: str = Field(..., min_length=1, max_length=50_000)
    source_language: Optional[str] = Field(None, description="Auto-detect if omitted")
    target_language: str = Field(..., min_length=2, max_length=50)


class TranslationResponse(BaseModel):
    """Translation result."""

    translated_text: str
    source_language: Optional[str] = None
    target_language: str
    confidence: Optional[float] = None


# ── Summarisation ──────────────────────────────────────────────────────────────

class SummarizeRequest(BaseModel):
    """Payload for POST /ai/summarize (text or conversation)."""

    text: Optional[str] = Field(None, description="Raw text to summarise")
    conversation_id: Optional[UUID] = Field(None, description="Conversation ID to summarise")
    max_length: Optional[int] = Field(None, ge=50, le=2000, description="Approximate max summary length")


class SummarizeResponse(BaseModel):
    """Summarisation result."""

    summary: str
    original_length: int
    summary_length: int


# ── Execution History ──────────────────────────────────────────────────────────

class ExecutionHistoryResponse(BaseModel):
    """Single execution record for history listing."""

    id: UUID
    agent_id: Optional[UUID] = None
    agent_type: Optional[str] = None
    tenant_id: UUID
    status: str
    input: Optional[dict[str, Any]] = None
    output: Optional[dict[str, Any]] = None
    tokens_used: Optional[int] = None
    duration_ms: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Report Generation ──────────────────────────────────────────────────────────

class GenerateReportRequest(BaseModel):
    """Payload for generating an AI-powered report."""

    tenant_id: UUID
    metric_data: dict[str, Any] = Field(..., description="Structured metric data")
    report_type: str = Field(..., description="e.g. weekly, monthly, campaign, pipeline")


class GenerateReportResponse(BaseModel):
    """Generated narrative report."""

    report: str
    report_type: str
    summary: Optional[str] = None
