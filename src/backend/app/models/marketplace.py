"""Marketplace models — installation records for plugins/extensions."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class MarketplaceInstallation(BaseModel):
    """Tracks installation of a marketplace listing in a workspace."""

    __tablename__ = "marketplace_installations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)
    version_installed: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="installed",
        index=True,
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
    )
    installed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    installed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    uninstalled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<MarketplaceInstallation {self.id} listing={self.listing_id} status={self.status}>"
