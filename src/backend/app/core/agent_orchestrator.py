"""
Agent Orchestrator — built-in registry of 12 specialised AI agent roles,
execution engine, tool dispatcher, conversation runner, and execution history.

This module provides the in-memory agent definitions and orchestration logic.
The orchestrator uses an OpenAI-compatible HTTP client (httpx) for LLM calls.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.ai import AIAgent, AIAgentExecution, Conversation, Message

logger = logging.getLogger("amc.core.agent_orchestrator")

# ── Tool catalog: 15+ tools across 11 categories ──────────────────────────────

TOOLS_CATALOG: dict[str, dict[str, Any]] = {
    "crm_get_contact": {
        "name": "crm_get_contact",
        "category": "CRM",
        "description": "Retrieve a CRM contact by ID.",
        "parameters": {"type": "object", "properties": {"contact_id": {"type": "string"}}},
    },
    "crm_list_contacts": {
        "name": "crm_list_contacts",
        "category": "CRM",
        "description": "List CRM contacts with optional filters.",
        "parameters": {"type": "object", "properties": {"limit": {"type": "integer"}, "offset": {"type": "integer"}}},
    },
    "crm_get_deal": {
        "name": "crm_get_deal",
        "category": "CRM",
        "description": "Retrieve a deal by ID.",
        "parameters": {"type": "object", "properties": {"deal_id": {"type": "string"}}},
    },
    "marketing_list_campaigns": {
        "name": "marketing_list_campaigns",
        "category": "Marketing",
        "description": "List marketing campaigns for a tenant.",
        "parameters": {"type": "object", "properties": {"tenant_id": {"type": "string"}, "status": {"type": "string"}}},
    },
    "marketing_get_campaign": {
        "name": "marketing_get_campaign",
        "category": "Marketing",
        "description": "Retrieve a campaign by ID.",
        "parameters": {"type": "object", "properties": {"campaign_id": {"type": "string"}}},
    },
    "content_generate": {
        "name": "content_generate",
        "category": "Content",
        "description": "Generate marketing copy for a given brief.",
        "parameters": {"type": "object", "properties": {"brief": {"type": "string"}, "tone": {"type": "string"}, "length": {"type": "string"}}},
    },
    "content_analyze": {
        "name": "content_analyze",
        "category": "Content",
        "description": "Analyze content readability, sentiment, and SEO.",
        "parameters": {"type": "object", "properties": {"text": {"type": "string"}}},
    },
    "analytics_get_metrics": {
        "name": "analytics_get_metrics",
        "category": "Analytics",
        "description": "Retrieve analytics metrics for a tenant.",
        "parameters": {"type": "object", "properties": {"tenant_id": {"type": "string"}, "metric": {"type": "string"}, "period": {"type": "string"}}},
    },
    "analytics_get_report": {
        "name": "analytics_get_report",
        "category": "Analytics",
        "description": "Generate a structured analytics report.",
        "parameters": {"type": "object", "properties": {"tenant_id": {"type": "string"}, "report_type": {"type": "string"}}},
    },
    "search_knowledge": {
        "name": "search_knowledge",
        "category": "Search",
        "description": "Search the knowledge base for relevant documents.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "tenant_id": {"type": "string"}, "limit": {"type": "integer"}}},
    },
    "social_get_insights": {
        "name": "social_get_insights",
        "category": "Social",
        "description": "Retrieve social media analytics/insights.",
        "parameters": {"type": "object", "properties": {"platform": {"type": "string"}, "period": {"type": "string"}}},
    },
    "email_get_templates": {
        "name": "email_get_templates",
        "category": "Email",
        "description": "List available email templates.",
        "parameters": {"type": "object", "properties": {"tenant_id": {"type": "string"}}},
    },
    "email_generate_subject": {
        "name": "email_generate_subject",
        "category": "Email",
        "description": "Generate email subject line variants.",
        "parameters": {"type": "object", "properties": {"topic": {"type": "string"}, "tone": {"type": "string"}}},
    },
    "data_export": {
        "name": "data_export",
        "category": "Data",
        "description": "Export data in a requested format (CSV, JSON).",
        "parameters": {"type": "object", "properties": {"entity": {"type": "string"}, "format": {"type": "string"}}},
    },
    "web_fetch": {
        "name": "web_fetch",
        "category": "Web",
        "description": "Fetch content from a URL.",
        "parameters": {"type": "object", "properties": {"url": {"type": "string"}}},
    },
    "system_info": {
        "name": "system_info",
        "category": "System",
        "description": "Get system information (uptime, version, health).",
        "parameters": {"type": "object", "properties": {}},
    },
    "knowledge_retrieve": {
        "name": "knowledge_retrieve",
        "category": "Knowledge",
        "description": "Retrieve a knowledge document by ID.",
        "parameters": {"type": "object", "properties": {"document_id": {"type": "string"}}},
    },
}

# ── Agent Registry: 12 specialised roles ───────────────────────────────────────

AGENT_REGISTRY: dict[str, dict[str, Any]] = {
    "copywriter": {
        "type": "copywriter",
        "name": "Copywriter Agent",
        "description": "Crafts compelling marketing copy for ads, emails, landing pages, blogs, and social posts.",
        "system_prompt": (
            "You are an expert marketing copywriter. Your role is to create "
            "persuasive, on-brand copy that drives conversions. Adapt your tone "
            "to the audience and channel. Always deliver ready-to-publish text."
        ),
        "default_tools": ["content_generate", "content_analyze", "email_generate_subject"],
    },
    "designer": {
        "type": "designer",
        "name": "Designer Agent",
        "description": "Generates visual concepts, image descriptions, and layout suggestions for marketing collateral.",
        "system_prompt": (
            "You are a creative design agent. You help generate image descriptions, "
            "visual concepts, and layout recommendations. Think in terms of colour "
            "palettes, typography, composition, and brand consistency."
        ),
        "default_tools": ["content_generate"],
    },
    "strategist": {
        "type": "strategist",
        "name": "Strategist Agent",
        "description": "Develops marketing strategies, campaign plans, and go-to-market recommendations.",
        "system_prompt": (
            "You are a senior marketing strategist. You analyse data, identify "
            "opportunities, and build comprehensive marketing plans. Your "
            "recommendations are data-informed, audience-centric, and ROI-focused."
        ),
        "default_tools": ["analytics_get_metrics", "analytics_get_report", "marketing_list_campaigns"],
    },
    "analyst": {
        "type": "analyst",
        "name": "Analyst Agent",
        "description": "Analyses campaign performance, creates reports, and extracts actionable insights from data.",
        "system_prompt": (
            "You are a data analyst specialising in marketing metrics. You "
            "interpret campaign data, identify trends, and present clear "
            "actionable insights. Always back your conclusions with data."
        ),
        "default_tools": ["analytics_get_metrics", "analytics_get_report", "data_export"],
    },
    "seo": {
        "type": "seo",
        "name": "SEO Agent",
        "description": "Optimises content for search engines — keyword research, on-page SEO, and technical audits.",
        "system_prompt": (
            "You are an SEO specialist. You understand search engine algorithms, "
            "keyword strategy, on-page optimisation, and technical SEO. Provide "
            "concrete, implementable recommendations."
        ),
        "default_tools": ["content_analyze", "search_knowledge", "web_fetch"],
    },
    "social": {
        "type": "social",
        "name": "Social Media Agent",
        "description": "Manages social media content calendars, post generation, and engagement analysis.",
        "system_prompt": (
            "You are a social media manager. You create platform-optimised "
            "content, schedule posts, analyse engagement, and recommend "
            "strategies to grow audience and reach."
        ),
        "default_tools": ["social_get_insights", "content_generate"],
    },
    "email": {
        "type": "email",
        "name": "Email Marketing Agent",
        "description": "Designs email campaigns, subject lines, and automated drip sequences.",
        "system_prompt": (
            "You are an email marketing specialist. You craft engaging email "
            "campaigns, write high-converting subject lines, and design "
            "automated nurture sequences. You understand deliverability and "
            "segmentation."
        ),
        "default_tools": ["email_get_templates", "email_generate_subject", "content_generate"],
    },
    "campaign": {
        "type": "campaign",
        "name": "Campaign Manager Agent",
        "description": "Orchestrates multi-channel campaigns — planning, execution, tracking, and optimisation.",
        "system_prompt": (
            "You are a campaign manager. You plan, execute, and optimise "
            "multi-channel marketing campaigns. Coordinate across teams, "
            "set KPIs, track performance, and pivot based on results."
        ),
        "default_tools": [
            "marketing_list_campaigns", "marketing_get_campaign",
            "analytics_get_metrics", "content_generate",
        ],
    },
    "data": {
        "type": "data",
        "name": "Data Agent",
        "description": "Queries, transforms, and exports marketing data from multiple sources.",
        "system_prompt": (
            "You are a data engineer focused on marketing data. You help "
            "query datasets, transform data, and export in the right format. "
            "You ensure data integrity and provide clear documentation."
        ),
        "default_tools": ["data_export", "analytics_get_metrics", "crm_list_contacts"],
    },
    "support": {
        "type": "support",
        "name": "Support Agent",
        "description": "Answers customer queries, resolves issues, and escalates when needed using knowledge base.",
        "system_prompt": (
            "You are a customer support agent. You answer questions, resolve "
            "issues, and provide helpful information. Be empathetic, accurate, "
            "and concise. Escalate complex issues when necessary."
        ),
        "default_tools": ["search_knowledge", "knowledge_retrieve", "crm_get_contact"],
    },
    "workflow": {
        "type": "workflow",
        "name": "Workflow Automation Agent",
        "description": "Designs and triggers automated marketing workflows, sequences, and task pipelines.",
        "system_prompt": (
            "You are a workflow automation expert. You design automated "
            "marketing sequences, trigger-based campaigns, and task pipelines. "
            "Think in terms of triggers, conditions, actions, and loops."
        ),
        "default_tools": ["marketing_list_campaigns", "email_get_templates", "data_export"],
    },
    "marketplace": {
        "type": "marketplace",
        "name": "Marketplace Agent",
        "description": "Manages marketplace listings, reviews, and vendor communications.",
        "system_prompt": (
            "You are a marketplace operations agent. You manage product "
            "listings, monitor reviews, handle vendor communications, and "
            "optimise marketplace performance."
        ),
        "default_tools": ["crm_list_contacts", "content_generate", "analytics_get_metrics"],
    },
}

# Supported LLM providers
SUPPORTED_PROVIDERS = {"opencode", "openai", "anthropic", "azure", "custom"}


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class AgentOrchestrator:
    """Orchestrates AI agent execution, tool dispatch, conversation management,
    and execution history retrieval.

    Uses an OpenAI-compatible HTTP client (httpx) for LLM inference.
    Provider, model, and endpoint are configurable via ``settings``.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Agent Registry Access ──────────────────────────────────────────────────

    @staticmethod
    def list_agents() -> list[dict[str, Any]]:
        """Return all built-in agent definitions."""
        return list(AGENT_REGISTRY.values())

    @staticmethod
    def get_agent(agent_type: str) -> dict[str, Any]:
        """Get a single agent definition by type.

        Raises:
            ValidationException: If the agent type is unknown.
        """
        agent = AGENT_REGISTRY.get(agent_type)
        if agent is None:
            raise ValidationException(
                detail=f"Unknown agent type '{agent_type}'. "
                       f"Available: {', '.join(sorted(AGENT_REGISTRY))}"
            )
        return agent

    # ── Agent Execution ───────────────────────────────────────────────────────

    async def execute_agent(
        self,
        agent_type: str,
        tenant_id: UUID,
        input_data: dict[str, Any],
        conversation_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        """Execute an AI agent with the given input.

        Steps:
        1. Look up the agent definition.
        2. Find or lazily create an ``AIAgent`` record for this tenant+type.
        3. Build a prompt from the system prompt + input.
        4. Call the LLM via ``_call_llm``.
        5. Record the execution in ``AIAgentExecution``.
        6. Optionally attach the exchange to a conversation.

        Returns a result dict with status, output, tokens_used, duration_ms.
        """
        agent_def = self.get_agent(agent_type)
        start_time = time.monotonic()

        # Find or create the tenant-scoped AIAgent record
        ai_agent = await self._resolve_agent_record(agent_def, tenant_id)

        # Build the conversation context
        messages = self._build_messages(agent_def, input_data, conversation_id)

        # Call the LLM
        try:
            llm_response = await self._call_llm(messages)
            output_text = llm_response.get("content", "")
            tokens_used = llm_response.get("tokens_used", 0)
            status = "completed"
            error = None
        except Exception as exc:
            logger.exception("LLM call failed for agent %s", agent_type)
            output_text = ""
            tokens_used = 0
            status = "failed"
            error = str(exc)

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Record execution
        execution = AIAgentExecution(
            agent_id=ai_agent.id,
            tenant_id=tenant_id,
            session_id=str(conversation_id) if conversation_id else None,
            input=input_data,
            output={"content": output_text} if output_text else None,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
            status=status,
            error=error,
        )
        self.db.add(execution)
        await self.db.flush()
        await self.db.refresh(execution)

        # Update agent stats
        ai_agent.total_executions = (ai_agent.total_executions or 0) + 1
        if duration_ms and ai_agent.avg_response_time_ms:
            ai_agent.avg_response_time_ms = (
                (ai_agent.avg_response_time_ms * (ai_agent.total_executions - 1) + duration_ms)
                / ai_agent.total_executions
            )
        elif duration_ms:
            ai_agent.avg_response_time_ms = float(duration_ms)

        # If conversation is provided, append messages
        if conversation_id and output_text:
            await self._append_to_conversation(
                conversation_id=conversation_id,
                user_content=str(input_data.get("prompt", input_data.get("message", str(input_data)))),
                assistant_content=output_text,
                user_id=user_id,
                tenant_id=tenant_id,
            )

        await self.db.flush()

        return {
            "agent_type": agent_type,
            "status": status,
            "output": {"content": output_text} if output_text else None,
            "execution_id": execution.id,
            "tokens_used": tokens_used,
            "duration_ms": duration_ms,
            "error": error,
        }

    async def execute_tool(self, tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name with the given parameters.

        This is a stub dispatch — in production each tool would call its
        respective service method.  Returns a standard result dict.
        """
        tool_def = TOOLS_CATALOG.get(tool_name)
        if tool_def is None:
            raise ValidationException(detail=f"Unknown tool '{tool_name}'")

        logger.info("Executing tool %s with params %s", tool_name, params)

        # Stub: return a simulated result
        return {
            "tool": tool_name,
            "category": tool_def["category"],
            "status": "success",
            "result": f"Simulated result for {tool_name}",
            "params": params,
        }

    # ── Conversation Management ────────────────────────────────────────────────

    async def create_conversation(
        self,
        title: Optional[str],
        user_id: UUID,
        tenant_id: UUID,
        agent_type: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation thread.

        Optionally associate with an agent type by finding or creating the
        corresponding ``AIAgent`` record.
        """
        agent_id: Optional[UUID] = None
        if agent_type:
            agent_def = self.get_agent(agent_type)
            ai_agent = await self._resolve_agent_record(agent_def, tenant_id)
            agent_id = ai_agent.id

        conv = Conversation(
            tenant_id=tenant_id,
            user_id=user_id,
            agent_id=agent_id,
            title=title or f"Conversation with {agent_type or 'AI'}",
        )
        self.db.add(conv)
        await self.db.flush()
        await self.db.refresh(conv)
        logger.info("Created conversation %s for tenant %s", conv.id, tenant_id)
        return conv

    async def run_conversation(
        self,
        conversation_id: UUID,
        message_content: str,
        user_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Send a message in a conversation and get an AI response.

        Looks up the conversation, appends the user message, determines the
        agent type from the conversation's associated agent, executes the
        agent, and returns the assistant response.
        """
        conv = await self.db.get(Conversation, conversation_id)
        if conv is None:
            raise NotFoundException(detail=f"Conversation {conversation_id} not found")

        # Determine agent type from linked agent record or default to 'support'
        agent_type = "support"
        if conv.agent_id:
            ai_agent = await self.db.get(AIAgent, conv.agent_id)
            if ai_agent:
                agent_type = ai_agent.agent_type

        # Save user message
        user_msg = Message(
            conversation_id=conversation_id,
            role="user",
            content=message_content,
            metadata={"user_id": str(user_id)},
        )
        self.db.add(user_msg)

        # Execute the agent
        result = await self.execute_agent(
            agent_type=agent_type,
            tenant_id=tenant_id,
            input_data={"message": message_content},
            conversation_id=conversation_id,
            user_id=user_id,
        )

        return result

    async def get_conversation_history(
        self,
        conversation_id: UUID,
    ) -> Optional[Conversation]:
        """Fetch a conversation with its messages eagerly loaded."""
        stmt = (
            select(Conversation)
            .where(Conversation.id == conversation_id)
        )
        result = await self.db.execute(stmt)
        conv = result.scalars().first()
        if conv is None:
            raise NotFoundException(detail=f"Conversation {conversation_id} not found")
        # Eagerly load messages
        await self.db.refresh(conv, ["messages"])
        return conv

    async def list_conversations(
        self,
        tenant_id: UUID,
        user_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Conversation], int]:
        """List conversations for a tenant, optionally filtered by user."""
        stmt = select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.is_archived == False,  # noqa: E712
        )
        count_stmt = select(func.count()).select_from(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.is_archived == False,  # noqa: E712
        )

        if user_id:
            stmt = stmt.where(Conversation.user_id == user_id)
            count_stmt = count_stmt.where(Conversation.user_id == user_id)

        stmt = stmt.order_by(desc(Conversation.updated_at)).offset(skip).limit(limit)

        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    # ── Execution History ─────────────────────────────────────────────────────

    async def get_execution_history(
        self,
        agent_type: str,
        tenant_id: UUID,
        limit: int = 10,
    ) -> list[AIAgentExecution]:
        """Retrieve recent execution records for an agent type within a tenant."""
        # Find AIAgent records of this type for the tenant
        agent_subq = (
            select(AIAgent.id)
            .where(
                AIAgent.tenant_id == tenant_id,
                AIAgent.agent_type == agent_type,
            )
            .subquery()
        )
        stmt = (
            select(AIAgentExecution)
            .where(
                AIAgentExecution.agent_id.in_(agent_subq),
                AIAgentExecution.tenant_id == tenant_id,
            )
            .order_by(desc(AIAgentExecution.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ── Internal Helpers ──────────────────────────────────────────────────────

    async def _resolve_agent_record(
        self, agent_def: dict[str, Any], tenant_id: UUID
    ) -> AIAgent:
        """Find an existing AIAgent record for this tenant+type, or create one.

        This lazy-initialises the agent record the first time it is used.
        """
        stmt = select(AIAgent).where(
            AIAgent.tenant_id == tenant_id,
            AIAgent.agent_type == agent_def["type"],
            AIAgent.is_active == True,  # noqa: E712
        )
        result = await self.db.execute(stmt)
        agent = result.scalars().first()
        if agent is None:
            agent = AIAgent(
                tenant_id=tenant_id,
                name=agent_def["name"],
                slug=agent_def["type"],
                agent_type=agent_def["type"],
                description=agent_def["description"],
                system_prompt=agent_def["system_prompt"],
                tools=agent_def.get("default_tools", []),
            )
            self.db.add(agent)
            await self.db.flush()
            await self.db.refresh(agent)
            logger.info("Created AIAgent record %s for tenant %s", agent.id, tenant_id)
        return agent

    def _build_messages(
        self,
        agent_def: dict[str, Any],
        input_data: dict[str, Any],
        conversation_id: Optional[UUID] = None,
    ) -> list[dict[str, str]]:
        """Build the message list for the LLM call.

        Includes the system prompt and the user input.
        """
        messages: list[dict[str, str]] = [
            {"role": "system", "content": agent_def["system_prompt"]},
        ]

        # Use the input as the user message
        user_message = input_data.get("prompt") or input_data.get("message") or str(input_data)
        messages.append({"role": "user", "content": user_message})

        return messages

    async def _call_llm(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """Call the configured LLM provider via an OpenAI-compatible HTTP API.

        Returns a dict with ``content`` and ``tokens_used``.

        The provider endpoint and model are read from ``settings``.
        Falls back to a local simulation when no provider is configured.
        """
        provider = getattr(settings, "ai_provider", "").lower() or "opencode"
        model = getattr(settings, "ai_model", "big-pickle")
        api_key = getattr(settings, "ai_api_key", None)
        base_url = getattr(settings, "ai_base_url", None)

        # If no explicit provider config, simulate a response
        if not api_key and not base_url:
            return await self._simulate_llm_call(messages)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 2048,
            "temperature": 0.7,
        }

        url = f"{base_url.rstrip('/')}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                choice = data["choices"][0]
                content = choice["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)
                return {"content": content, "tokens_used": tokens_used}
        except Exception as exc:
            logger.warning("LLM call failed, falling back to simulation: %s", exc)
            return await self._simulate_llm_call(messages)

    async def _simulate_llm_call(
        self, messages: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Simulate an LLM response when no provider is configured.

        Useful for development and testing.
        """
        system_msg = next((m["content"] for m in messages if m["role"] == "system"), "")
        user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")

        # Simple keyword-based response
        content = (
            f"I analysed your request and here is my response.\n\n"
            f"**Context:** {user_msg[:200]}{'...' if len(user_msg) > 200 else ''}\n\n"
            f"As an AI assistant, I've processed your input and prepared the "
            f"requested output. In production, this would use a real LLM provider "
            f"to generate high-quality, contextually relevant content."
        )

        return {"content": content, "tokens_used": len(user_msg.split()) * 2}

    async def _append_to_conversation(
        self,
        conversation_id: UUID,
        user_content: str,
        assistant_content: str,
        user_id: Optional[UUID],
        tenant_id: UUID,
    ) -> None:
        """Append user and assistant messages to an existing conversation."""
        # User message is already saved in run_conversation; save assistant
        assistant_msg = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
        )
        self.db.add(assistant_msg)

        # Update conversation message count
        conv = await self.db.get(Conversation, conversation_id)
        if conv:
            conv.message_count = (conv.message_count or 0) + 1
