"""AI Router — agents, conversations, content generation, analysis, classification,
translation, summarisation, and execution history.

All endpoints (unless noted) require an authenticated active user and tenant
context.  Responses use the standard ``{data, meta, links}`` envelope for lists
and ``{data: {...}}`` for single resources.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.core.agent_orchestrator import AgentOrchestrator
from app.models.auth import User
from app.schemas.ai import (
    AgentDefinition,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentListResponse,
    ClassificationRequest,
    ClassificationResponse,
    ContentAnalyzeRequest,
    ContentAnalyzeResponse,
    ContentGenerateRequest,
    ContentGenerateResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    ExecutionHistoryResponse,
    GenerateReportRequest,
    GenerateReportResponse,
    LeadScoreRequest,
    LeadScoreResponse,
    MessageCreate,
    MessageResponse,
    SummarizeRequest,
    SummarizeResponse,
    TranslationRequest,
    TranslationResponse,
)
from app.schemas.base import build_list_response, build_single_response
from app.services.ai_service import AIService

router = APIRouter(prefix="/ai", tags=["ai"])


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Definitions
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/agents")
async def list_agents() -> dict:
    """List all available AI agent definitions (built-in catalog).

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    agents = AgentOrchestrator.list_agents()
    return build_single_response(
        AgentListResponse(
            agents=[AgentDefinition(**a) for a in agents],
            total=len(agents),
        ),
    )


@router.get("/agents/{agent_type}")
async def get_agent(agent_type: str) -> dict:
    """Get a single agent definition by type.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    try:
        agent = AgentOrchestrator.get_agent(agent_type)
        return build_single_response(AgentDefinition(**agent))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/agents/{agent_type}/execute")
async def execute_agent(
    agent_type: str,
    body: AgentExecuteRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Execute an AI agent with the given input.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = body.tenant_id
    orchestrator = AgentOrchestrator(db)
    result = await orchestrator.execute_agent(
        agent_type=agent_type,
        tenant_id=tenant_id,
        input_data=body.input_data,
        conversation_id=body.conversation_id,
        user_id=body.user_id or current_user.id,
    )
    return build_single_response(AgentExecuteResponse(**result))


# ═══════════════════════════════════════════════════════════════════════════════
# Conversations
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/conversations", status_code=201)
async def create_conversation(
    body: ConversationCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new conversation thread.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    orchestrator = AgentOrchestrator(db)
    conv = await orchestrator.create_conversation(
        title=body.title,
        user_id=body.user_id or current_user.id,
        tenant_id=body.tenant_id,
        agent_type=body.agent_type,
    )
    return build_single_response(ConversationResponse.model_validate(conv))


@router.get("/conversations")
async def list_conversations(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    user_id: UUID | None = Query(None),
) -> dict:
    """List conversations for the current tenant.

    Optionally filter by ``user_id``.
    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    skip = (page - 1) * limit
    orchestrator = AgentOrchestrator(db)
    items, total = await orchestrator.list_conversations(
        tenant_id=tenant_id,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )
    return build_list_response(
        data=[ConversationResponse.model_validate(c) for c in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single conversation with its messages.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    orchestrator = AgentOrchestrator(db)
    conv = await orchestrator.get_conversation_history(conversation_id)
    # Eagerly load messages via relationship
    messages = conv.messages if hasattr(conv, "messages") else []
    response = ConversationDetailResponse(
        id=conv.id,
        tenant_id=conv.tenant_id,
        user_id=conv.user_id,
        title=conv.title,
        agent_id=conv.agent_id,
        message_count=conv.message_count or len(messages),
        is_archived=conv.is_archived,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
        messages=[MessageResponse.model_validate(m) for m in messages],
    )
    return build_single_response(response)


@router.post("/conversations/{conversation_id}/messages", status_code=201)
async def send_message(
    conversation_id: UUID,
    body: MessageCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a message in a conversation and get an AI response.

    The AI response is recorded as an assistant message in the same conversation.
    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = body.tenant_id
    orchestrator = AgentOrchestrator(db)
    result = await orchestrator.run_conversation(
        conversation_id=conversation_id,
        message_content=body.content,
        user_id=body.user_id or current_user.id,
        tenant_id=tenant_id,
    )
    return build_single_response(AgentExecuteResponse(**result))


# ═══════════════════════════════════════════════════════════════════════════════
# Content Generation & Analysis
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/content/generate")
async def generate_content(
    body: ContentGenerateRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate marketing content using AI.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = AIService(db)
    result = await service.generate_content(
        tenant_id=body.tenant_id,
        prompt=body.prompt,
        content_type=body.content_type,
        tone=body.tone,
        length=body.length,
    )
    return build_single_response(ContentGenerateResponse(**result))


@router.post("/content/analyze")
async def analyze_content(
    body: ContentAnalyzeRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Analyse existing content, a campaign, or generate an image description.

    Three modes:
    - ``campaign_id`` set → campaign analysis
    - ``image_url`` set → image description generation
    - ``content_text`` set → content analysis

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = AIService(db)

    if body.image_url:
        result = await service.generate_image_description(
            image_url=body.image_url,
            style=body.style,
        )
        return build_single_response(
            ContentAnalyzeResponse(
                analysis=result.get("alt_text", ""),
                analysis_type="image_description",
                image_prompt=result.get("image_prompt"),
                alt_text=result.get("alt_text"),
            ),
        )

    if body.campaign_id:
        result = await service.analyze_campaign(
            campaign_id=body.campaign_id,
            tenant_id=body.tenant_id,
        )
        return build_single_response(ContentAnalyzeResponse(**result))

    # Default: content text analysis
    text_to_analyze = body.content_text or ""
    # Use the SEO agent for content analysis
    orchestrator = AgentOrchestrator(db)
    analysis_result = await orchestrator.execute_agent(
        agent_type="seo",
        tenant_id=body.tenant_id,
        input_data={
            "prompt": f"Analyse the following content for quality, readability, "
            f"and SEO optimisation. Provide specific recommendations.\n\n{text_to_analyze}",
        },
    )
    output_content = analysis_result.get("output", {}).get("content", "")

    # Extract suggestions
    suggestions = []
    if output_content:
        for line in output_content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("-") or stripped.startswith("*"):
                suggestions.append(stripped.lstrip("-* "))

    return build_single_response(
        ContentAnalyzeResponse(
            analysis=output_content,
            analysis_type="content",
            suggestions=suggestions[:10] if suggestions else None,
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Lead Scoring
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/leads/score")
async def score_lead(
    body: LeadScoreRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Score a lead (contact) using AI.

    Returns score 0-100, tier, and rationale.
    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = AIService(db)
    result = await service.score_lead(
        contact_id=body.contact_id,
        tenant_id=body.tenant_id,
    )
    return build_single_response(LeadScoreResponse(**result))


# ═══════════════════════════════════════════════════════════════════════════════
# Intent Classification
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/classify")
async def classify_intent(
    body: ClassificationRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Classify the intent of a piece of text.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = AIService(db)
    result = await service.classify_intent(text=body.text)
    return build_single_response(ClassificationResponse(**result))


# ═══════════════════════════════════════════════════════════════════════════════
# Execution History
# ═══════════════════════════════════════════════════════════════════════════════


@router.get("/executions/{agent_type}")
async def get_execution_history(
    agent_type: str,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
) -> dict:
    """Get execution history for an agent type.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    orchestrator = AgentOrchestrator(db)
    items = await orchestrator.get_execution_history(
        agent_type=agent_type,
        tenant_id=tenant_id,
        limit=limit,
    )
    return build_single_response(
        {
            "agent_type": agent_type,
            "executions": [ExecutionHistoryResponse.model_validate(e) for e in items],
            "total": len(items),
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Translation
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/translate")
async def translate_text(
    body: TranslationRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Translate content to a target language.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = AIService(db)
    result = await service.translate_text(
        text=body.text,
        target_language=body.target_language,
        source_language=body.source_language,
    )
    return build_single_response(TranslationResponse(**result))


# ═══════════════════════════════════════════════════════════════════════════════
# Summarisation
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/summarize")
async def summarize_content(
    body: SummarizeRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Summarise text or a conversation.

    If ``conversation_id`` is provided, summarises that conversation.
    Otherwise summarises the provided ``text``.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = AIService(db)

    if body.conversation_id:
        result = await service.summarize_conversation(
            conversation_id=body.conversation_id,
        )
    elif body.text:
        result = await service.summarize_text(
            text=body.text,
            max_length=body.max_length,
        )
    else:
        raise HTTPException(status_code=422, detail="Either text or conversation_id is required")

    return build_single_response(SummarizeResponse(**result))


# ═══════════════════════════════════════════════════════════════════════════════
# Report Generation
# ═══════════════════════════════════════════════════════════════════════════════


@router.post("/reports/generate")
async def generate_report(
    body: GenerateReportRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Generate a narrative report from structured metric data.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    service = AIService(db)
    result = await service.generate_report(
        tenant_id=body.tenant_id,
        metric_data=body.metric_data,
        report_type=body.report_type,
    )
    return build_single_response(GenerateReportResponse(**result))
