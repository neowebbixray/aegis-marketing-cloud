"""SEO models — keyword tracking, site audits, backlink data.

All models are multi-tenant (tenant_id scoped).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class SeoKeyword(BaseModel):
    """Tracked SEO keyword with ranking position data.

    Stores the keyword, target URL, search-engine scope, and current/previous
    ranking information. Tags are stored as a JSONB array for flexible
    classification (e.g. ``["branded", "high-priority"]``).
    """

    __tablename__ = "seo_keywords"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    keyword: Mapped[str] = mapped_column(String(500), nullable=False)
    target_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    search_engine: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="google",
    )
    location: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    tags: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    current_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    search_volume: Mapped[int | None] = mapped_column(Integer, nullable=True)
    difficulty_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<SeoKeyword {self.keyword} (rank={self.current_rank})>"
