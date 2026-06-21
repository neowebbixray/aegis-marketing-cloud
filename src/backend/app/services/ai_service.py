"""
AI service for lead scoring, content generation, and analysis.

Provides the ``AIService`` class used by the AI API endpoints.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException


class AIService:
    """AI-powered service for lead scoring, content generation, and analysis."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Rule-Based Lead Scoring ────────────────────────────────────────

    async def score_lead_rule_based(
        self,
        contact_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """
        Score a lead (contact) using rule-based scoring.

        Evaluates the contact's profile and engagement data against
        predefined scoring rules to produce a score from 0-100.

        Args:
            contact_id: Contact to score.
            tenant_id: Tenant context.

        Returns:
            Dict with ``contact_id``, ``score``, ``rationale``, ``tier``.
        """
        from app.models.crm import Contact

        # Fetch contact details
        stmt = select(Contact).where(
            Contact.id == contact_id,
            Contact.tenant_id == tenant_id,
        )
        result = await self.db.execute(stmt)
        contact = result.scalars().first()
        if contact is None:
            raise NotFoundException(detail=f"Contact {contact_id} not found")

        # Initialize score and rationale
        score = 0
        rationale_parts = []

        # === Demographic Scoring ===
        # Job title scoring
        if contact.job_title:
            job_title_lower = contact.job_title.lower()
            # Executive titles
            if any(title in job_title_lower for title in ['ceo', 'cfo', 'cto', 'president', 'founder', 'owner']):
                score += 25
                rationale_parts.append("Executive job title (+25)")
            # Director/VP titles
            elif any(title in job_title_lower for title in ['director', 'vp', 'vice president', 'head of']):
                score += 20
                rationale_parts.append("Director/VP level job title (+20)")
            # Manager titles
            elif any(title in job_title_lower for title in ['manager', 'lead', 'principal', 'senior']):
                score += 15
                rationale_parts.append("Manager/Lead level job title (+15)")
            # Other professional titles
            elif any(title in job_title_lower for title in ['specialist', 'coordinator', 'analyst', 'engineer']):
                score += 10
                rationale_parts.append("Professional job title (+10)")

        # Company scoring
        if contact.company:
            if len(contact.company) > 0:
                score += 10
                rationale_parts.append("Has company information (+10)")

        # === Engagement Scoring ===
        # Email engagement (using tags as proxy)
        if contact.tags:
            tags_lower = [tag.lower() for tag in contact.tags]
            if any(tag in tags_lower for tag in ['newsletter', 'subscriber', 'email']):
                score += 15
                rationale_parts.append("Email engagement indicators (+15)")
            if any(tag in tags_lower for tag in ['webinar', 'event', 'demo']):
                score += 20
                rationale_parts.append("Event/webinar attendance (+20)")
            if any(tag in tags_lower for tag in ['pricing', 'product', 'trial']):
                score += 25
                rationale_parts.append("Product interest shown (+25)")

        # Source scoring
        if contact.source:
            source_lower = contact.source.lower()
            if source_lower in ['referral', 'website']:
                score += 15
                rationale_parts.append(f"High-quality source ({contact.source}) (+15)")
            elif source_lower in ['social', 'email']:
                score += 10
                rationale_parts.append(f"Medium-quality source ({contact.source}) (+10)")
            else:
                score += 5
                rationale_parts.append(f"Source: {contact.source} (+5)")

        # Lifecycle stage scoring
        lifecycle_scores = {
            'lead': 0,
            'qualified': 20,
            'opportunity': 30,
            'customer': 40,
            'churned': -10,
            'inactive': -20,
        }
        lifecycle_score = lifecycle_scores.get(contact.lifecycle_stage, 0)
        if lifecycle_score != 0:
            score += lifecycle_score
            rationale_parts.append(f"Lifecycle stage: {contact.lifecycle_stage} ({lifecycle_score:+d})")

        # === Negative Scoring (Penalties) ===
        if not contact.email or '@' not in contact.email:
            score -= 10
            rationale_parts.append("Missing or invalid email (-10)")
        if not contact.phone:
            score -= 5
            rationale_parts.append("Missing phone number (-5)")

        # Ensure score is within bounds
        score = max(0, min(100, score))

        # Determine tier
        if score >= 70:
            tier = "hot"
        elif score >= 40:
            tier = "warm"
        else:
            tier = "cold"

        rationale = "; ".join(rationale_parts) if rationale_parts else "Default scoring applied"

        return {
            "contact_id": contact_id,
            "score": score,
            "rationale": rationale,
            "tier": tier,
        }

    # ── Content Generation ────────────────────────────────────────────

    async def generate_content(
        self,
        tenant_id: UUID,
        prompt: str,
        content_type: str,
        tone: str = "professional",
        length: str = "medium",
    ) -> dict[str, Any]:
        """Generate marketing content using AI. (Placeholder)"""
        return {
            "content": f"Generated {content_type} content for: {prompt[:50]}...",
            "content_type": content_type,
            "tone": tone,
            "length": length,
        }

    async def generate_image_description(
        self,
        image_url: str,
        style: str | None = None,
    ) -> dict[str, Any]:
        """Generate an image description. (Placeholder)"""
        return {
            "alt_text": f"AI-generated description for image at {image_url}",
            "image_prompt": f"A {style or 'natural'} style image",
        }

    async def analyze_campaign(
        self,
        campaign_id: UUID,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Analyse a campaign's performance. (Placeholder)"""
        return {
            "campaign_id": str(campaign_id),
            "analysis": f"Campaign {campaign_id} analysed successfully",
            "analysis_type": "campaign_analysis",
        }
