"""Media models — assets with multi-tenant isolation and metadata."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class Asset(BaseModel):
    """Digital asset — file, image, video, document, or brand asset."""

    __tablename__ = "assets"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_backend: Mapped[str] = mapped_column(String(50), default="local")
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    alt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    meta_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=dict)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def __repr__(self) -> str:
        return f"<Asset {self.filename}>"
