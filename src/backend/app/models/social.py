"""Social models — SocialPost for scheduling and publishing.

All models are multi-tenant (tenant_id + workspace_id).
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class SocialPost(BaseModel):
    """A scheduled or published social media post."""

    __tablename__ = "social_posts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    media_urls: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, default=list)
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), default="draft")
    tags: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True, default=list)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column("extra_data", JSONB, nullable=True, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    platform_post_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    def __repr__(self) -> str:
        return f"<SocialPost {self.platform} ({self.status})>"
