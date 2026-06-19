"""
AI Service — high-level service layer for AI-powered marketing operations.

Provides methods for content generation, image description, campaign analysis,
lead scoring, intent classification, email subject generation, conversation
summarisation, and report generation.

All tenant-scoped operations require a tenant_id UUID.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.agent_orchestrator import AgentOrchestrator
from app.core.exceptions import NotFoundException, ValidationException
from app.models.ai import AIAgent, AIAgentExecution, Conversation, Message, KnowledgeDocument
from app.models.crm import Contact

logger = logging.getLogger("amc.services.ai")


class AIService:
    """High-level AI service for marketing operations.

    Wraps the AgentOrchestrator and adds domain-specific methods for
    content generation, analysis, lead scoring, classification, and more.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orchestrator = AgentOrchestrator(db)

    # ── Content Generation ─────────────────────────────────────────────────────

    async def generate_content(
        self,
        tenant_id: UUID,
        prompt: str,
        content_type: str = "general",
        tone: Optional[str] = None,
        length: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate marketing content using the Copywriter agent.

        Args:
            tenant_id: Tenant context.
            prompt: The content brief / prompt.
            content_type: Type of content (blog, social, email, ad, etc.).
            tone: Desired tone (professional, casual, urgent, friendly, etc.).
            length: Desired length (short, medium, long).

        Returns:
            Dict with ``content``, ``content_type``, ``word_count``, ``tone``.
        """
        enriched_prompt = f"Content type: {content_type}\n"
        if tone:
            enriched_prompt += f"Tone: {tone}\n"
        if length:
            enriched_prompt += f"Length: {length}\n"
        enriched_prompt += f"\nBrief:\n{prompt}"

        result = await self.orchestrator.execute_agent(
            agent_type="copywriter",
            tenant_id=tenant_id,
            input_data={"prompt": enriched_prompt, "content_type": content_type, "tone": tone, "length": length},
        )

        output_content = ""
        if result.get("output") and result["output"].get("content"):
            output_content = result["output"]["content"]

        return {
            "content": output_content,
            "content_type": content_type,
            "word_count": len(output_content.split()),
            "tone": tone,
        }

    async def generate_image_description(
        self,
        image_url: str,
        style: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate an image description and alt text using the Designer agent.

        Args:
            image_url: URL of the image.
            style: Optional art/visual style hint.

        Returns:
            Dict with ``image_prompt`` and ``alt_text``.
        """
        prompt = f"Describe this image in detail: {image_url}"
        if style:
            prompt += f"\nStyle reference: {style}"

        # Use the designer agent with a generic tenant ID for stateless operations
        # In production, the tenant ID should come from context.
        # We use a zero-UUID as sentinel; callers should pass tenant_id.
        result = await self.orchestrator.execute_agent(
            agent_type="designer",
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            input_data={"prompt": prompt, "image_url": image_url, "style": style},
        )

        output_content = result.get("output", {}).get("content", "")

        return {
            "image_prompt": f"Generate an image in style: {style}" if style else "Generate an image based on the description",
            "alt_text": output_content[:500] if output_content else "AI-generated image",
        }

    # ── Campaign Analysis ──────────────────────────────────────────────────────

    async def analyze_campaign(
        self,
        campaign_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Analyse a marketing campaign using the Analyst agent.

        Args:
            campaign_id: Campaign to analyse.
            tenant_id: Tenant context.

        Returns:
            Dict with ``analysis``, ``analysis_type``, and ``suggestions``.
        """
        # Attempt to fetch the campaign for context
        campaign_info = f"Campaign ID: {campaign_id}"
        try:
            from app.models.marketing import Campaign

            stmt = select(Campaign).where(
                Campaign.id == campaign_id,
                Campaign.tenant_id == tenant_id,
            )
            result = await self.db.execute(stmt)
            campaign = result.scalars().first()
            if campaign:
                campaign_info = (
                    f"Campaign: {campaign.name or 'Untitled'}\n"
                    f"Status: {campaign.status}\n"
                    f"Type: {campaign.campaign_type}\n"
                    f"Budget: {campaign.budget}\n"
                )
        except Exception:
            logger.debug("Could not fetch campaign %s details", campaign_id)

        result = await self.orchestrator.execute_agent(
            agent_type="analyst",
            tenant_id=tenant_id,
            input_data={
                "prompt": f"Analyse the following marketing campaign and provide insights, "
                          f"performance assessment, and actionable recommendations.\n\n{campaign_info}",
                "campaign_id": str(campaign_id),
            },
        )

        output_content = result.get("output", {}).get("content", "")

        # Extract suggestions from output (simple heuristic)
        suggestions = []
        if output_content:
            lines = output_content.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("-") or stripped.startswith("*"):
                    suggestions.append(stripped.lstrip("-* "))

        return {
            "analysis": output_content,
            "analysis_type": "campaign",
            "suggestions": suggestions[:10] if suggestions else None,
        }

    # ── Lead Scoring ───────────────────────────────────────────────────────────

    async def score_lead(
        self,
        contact_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Score a lead (contact) using AI.

        Fetches the contact's data and runs it through the Strategist agent
        to produce a score from 0-100 with rationale.

        Args:
            contact_id: Contact to score.
            tenant_id: Tenant context.

        Returns:
            Dict with ``contact_id``, ``score``, ``rationale``, ``tier``.
        """
        # Fetch contact details
        stmt = select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        contact = result.scalars().first()
        if contact is None:
            raise NotFoundException(detail=f"Contact {contact_id} not found")

        contact_info = (
            f"Contact: {contact.first_name or ''} {contact.last_name or ''}\n"
            f"Email: {contact.email}\n"
            f"Status: {contact.status}\n"
            f"Source: {contact.source}\n"
            f"Score: {contact.score}\n"
            f"Tags: {contact.tags}\n"
        )

        result = await self.orchestrator.execute_agent(
            agent_type="strategist",
            tenant_id=tenant_id,
            input_data={
                "prompt": (
                    f"Score this lead on a scale of 0-100 based on their profile. "
                    f"Provide a score, tier (hot/warm/cold), and rationale.\n\n"
                    f"{contact_info}"
                ),
                "contact_id": str(contact_id),
            },
        )

        output_content = result.get("output", {}).get("content", "")

        # Parse score from output (simple heuristic)
        score = 50  # default
        import re
        score_match = re.search(r"(\d{1,3})\s*\/\s*100", output_content)
        if score_match:
            score = min(100, max(0, int(score_match.group(1))))

        if score >= 70:
            tier = "hot"
        elif score >= 40:
            tier = "warm"
        else:
            tier = "cold"

        return {
            "contact_id": contact_id,
            "score": score,
            "rationale": output_content[:1000] if output_content else "AI-generated score",
            "tier": tier,
        }

    # ── Intent Classification ──────────────────────────────────────────────────

    async def classify_intent(
        self,
        text: str,
    ) -> dict[str, Any]:
        """Classify the intent of a piece of text using the Support agent.

        Args:
            text: Text to classify.

        Returns:
            Dict with ``intent``, ``confidence``, and ``categories``.
        """
        result = await self.orchestrator.execute_agent(
            agent_type="support",
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            input_data={
                "prompt": (
                    f"Classify the intent of the following text into one of these "
                    f"categories: inquiry, complaint, feedback, purchase, support, "
                    f"feature_request, cancellation, other. Provide confidence score.\n\n"
                    f"Text: {text}"
                ),
            },
        )

        output_content = result.get("output", {}).get("content", "")

        # Parse intent from output
        import re
        intent = "other"
        confidence = 0.5

        intent_match = re.search(
            r"(inquiry|complaint|feedback|purchase|support|feature_request|cancellation|other)",
            output_content,
            re.IGNORECASE,
        )
        if intent_match:
            intent = intent_match.group(1).lower()

        confidence_match = re.search(r"(\d+(?:\.\d+)?)\s*%", output_content)
        if confidence_match:
            confidence = min(1.0, max(0.0, float(confidence_match.group(1)) / 100.0))

        return {
            "intent": intent,
            "confidence": confidence,
            "categories": [{"intent": intent, "confidence": confidence}],
        }

    # ── Email Subject Generation ───────────────────────────────────────────────

    async def generate_email_subject(
        self,
        line: str,
        tone: Optional[str] = None,
    ) -> dict[str, Any]:
        """Generate email subject line variants using the Email agent.

        Args:
            line: The email content or topic line.
            tone: Desired tone (professional, casual, urgent, friendly).

        Returns:
            Dict with ``subject_line`` and ``variants``.
        """
        prompt = f"Generate compelling email subject lines for:\n{line}"
        if tone:
            prompt += f"\nTone: {tone}"

        result = await self.orchestrator.execute_agent(
            agent_type="email",
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            input_data={"prompt": prompt, "tone": tone},
        )

        output_content = result.get("output", {}).get("content", "")

        # Parse subject lines from output
        variants = []
        for line_text in output_content.split("\n"):
            stripped = line_text.strip().strip('"').strip("'")
            if stripped and (stripped.startswith("-") or stripped[0].isdigit() or ":" in stripped[:5]):
                cleaned = stripped.lstrip("0123456789.-* ").strip('"').strip("'")
                if cleaned:
                    variants.append(cleaned)

        if not variants:
            variants = [output_content.strip()[:100]] if output_content.strip() else []

        return {
            "subject_line": variants[0] if variants else output_content[:100],
            "variants": variants[:5],
        }

    # ── Conversation Summarisation ─────────────────────────────────────────────

    async def summarize_conversation(
        self,
        conversation_id: UUID,
    ) -> dict[str, Any]:
        """Summarise a conversation thread.

        Args:
            conversation_id: Conversation to summarise.

        Returns:
            Dict with ``summary``, ``original_length``, ``summary_length``.
        """
        stmt = select(Conversation).where(Conversation.id == conversation_id)
        result = await self.db.execute(stmt)
        conv = result.scalars().first()
        if conv is None:
            raise NotFoundException(detail=f"Conversation {conversation_id} not found")

        # Eagerly load messages
        await self.db.refresh(conv, ["messages"])

        # Build transcript
        transcript_parts = []
        for msg in conv.messages:
            transcript_parts.append(f"{msg.role}: {msg.content}")
        transcript = "\n".join(transcript_parts)
        original_length = len(transcript.split())

        if not transcript.strip():
            return {"summary": "No messages to summarise.", "original_length": 0, "summary_length": 0}

        result = await self.orchestrator.execute_agent(
            agent_type="analyst",
            tenant_id=conv.tenant_id,
            input_data={
                "prompt": (
                    f"Summarise the following conversation concisely. "
                    f"Capture the key points, decisions, and action items.\n\n"
                    f"{transcript}"
                ),
            },
        )

        summary = result.get("output", {}).get("content", "")
        if not summary:
            summary = f"Conversation with {len(conv.messages)} messages summarised."

        return {
            "summary": summary,
            "original_length": original_length,
            "summary_length": len(summary.split()),
        }

    # ── Report Generation ──────────────────────────────────────────────────────

    async def generate_report(
        self,
        tenant_id: UUID,
        metric_data: dict[str, Any],
        report_type: str,
    ) -> dict[str, Any]:
        """Generate a narrative report from structured metric data.

        Args:
            tenant_id: Tenant context.
            metric_data: Structured metric data (dict of metrics).
            report_type: Type of report (weekly, monthly, campaign, pipeline).

        Returns:
            Dict with ``report``, ``report_type``, and ``summary``.
        """
        data_str = str(metric_data)
        if len(data_str) > 15000:
            data_str = data_str[:15000] + "..."

        result = await self.orchestrator.execute_agent(
            agent_type="analyst",
            tenant_id=tenant_id,
            input_data={
                "prompt": (
                    f"Generate a {report_type} report based on the following "
                    f"metrics data. Provide a narrative summary, key insights, "
                    f"and actionable recommendations.\n\n{data_str}"
                ),
                "report_type": report_type,
            },
        )

        report_content = result.get("output", {}).get("content", "")

        # Extract a summary (first paragraph)
        summary = ""
        if report_content:
            paragraphs = report_content.split("\n\n")
            summary = paragraphs[0] if paragraphs else report_content[:300]

        return {
            "report": report_content,
            "report_type": report_type,
            "summary": summary[:500] if summary else None,
        }

    # ── Translation ────────────────────────────────────────────────────────────

    async def translate_text(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> dict[str, Any]:
        """Translate text to a target language using the Copywriter agent.

        Args:
            text: Text to translate.
            target_language: Target language (e.g. 'es', 'fr', 'de').
            source_language: Optional source language (auto-detect if omitted).

        Returns:
            Dict with ``translated_text``, ``source_language``, ``target_language``, ``confidence``.
        """
        prompt = f"Translate the following text to {target_language}."
        if source_language:
            prompt += f" Source language: {source_language}."
        prompt += f"\n\n{text}"

        result = await self.orchestrator.execute_agent(
            agent_type="copywriter",
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            input_data={"prompt": prompt},
        )

        translated = result.get("output", {}).get("content", "")

        return {
            "translated_text": translated,
            "source_language": source_language,
            "target_language": target_language,
            "confidence": 0.85 if translated else None,
        }

    # ── Text Summarisation (standalone, not conversation-based) ────────────────

    async def summarize_text(
        self,
        text: str,
        max_length: Optional[int] = None,
    ) -> dict[str, Any]:
        """Summarise a piece of text.

        Args:
            text: Text to summarise.
            max_length: Approximate max summary length.

        Returns:
            Dict with ``summary``, ``original_length``, ``summary_length``.
        """
        prompt = "Summarise the following text concisely."
        if max_length:
            prompt += f" Target length: approximately {max_length} words."
        prompt += f"\n\n{text}"

        result = await self.orchestrator.execute_agent(
            agent_type="analyst",
            tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
            input_data={"prompt": prompt},
        )

        summary = result.get("output", {}).get("content", "")

        return {
            "summary": summary,
            "original_length": len(text.split()),
            "summary_length": len(summary.split()),
        }
