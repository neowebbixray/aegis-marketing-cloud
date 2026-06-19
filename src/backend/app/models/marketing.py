"""Marketing models — Campaigns, Emails, Landing Pages, Funnels, Segments, Tags.

All models are multi-tenant (tenant_id + workspace_id).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin


class Campaign(BaseModel, SoftDeleteMixin):
    """Marketing campaign — draft → running → completed."""

    __tablename__ = "campaigns"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    campaign_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    target_audience: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    schedule_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    schedule_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_optimized: Mapped[bool] = mapped_column(Boolean, default=False)
    metrics: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<Campaign {self.name} ({self.status})>"


class EmailTemplate(BaseModel, SoftDeleteMixin):
    """Email template with HTML/text body and variable substitution."""

    __tablename__ = "email_templates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(998), nullable=False)
    preheader: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body_html: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    variables: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"<EmailTemplate {self.name}>"


class LandingPage(BaseModel, SoftDeleteMixin):
    """Landing page with block-based content editor support."""

    __tablename__ = "landing_pages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    published_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="draft")
    seo_meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    version: Mapped[int] = mapped_column(Integer, default=1)

    def __repr__(self) -> str:
        return f"<LandingPage {self.slug}>"


class Funnel(BaseModel, SoftDeleteMixin):
    """Marketing/sales funnel definition with conversion tracking."""

    __tablename__ = "funnels"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    steps: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    conversion_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    ai_optimized: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"<Funnel {self.name}>"


class Segment(BaseModel):
    """Contact segment defined by dynamic or static criteria."""

    __tablename__ = "segments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    criteria: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    contact_count: Mapped[int] = mapped_column(Integer, default=0)
    is_dynamic: Mapped[bool] = mapped_column(Boolean, default=True)

    def __repr__(self) -> str:
        return f"<Segment {self.name}>"


class Tag(BaseModel):
    """Tag for categorising contacts, campaigns, and content."""

    __tablename__ = "tags"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)

    def __repr__(self) -> str:
        return f"<Tag {self.name}>"
