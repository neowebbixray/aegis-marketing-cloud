"""SQLAlchemy model mixins that provide common columns and behaviours:
*   ``TimestampMixin`` — ``created_at`` / ``updated_at``
*   ``SoftDeleteMixin`` — ``deleted_at``, ``is_deleted``, ``restore()``
*   ``TenantMixin`` — ``tenant_id`` column
*   ``BaseModel`` — UUID primary key + all of the above
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


# ── TimestampMixin ───────────────────────────────────────────────────────────
class TimestampMixin:
    """Adds ``created_at`` and ``updated_at`` columns with defaults."""

    created_at: Mapped[datetime] = mapped_column(
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


# ── SoftDeleteMixin ──────────────────────────────────────────────────────────
class SoftDeleteMixin:
    """Adds ``deleted_at`` column plus ``is_deleted`` and ``restore()``."""

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Return ``True`` if this record is soft-deleted."""
        return self.deleted_at is not None

    def restore(self) -> None:
        """Mark this record as not deleted."""
        self.deleted_at = None

    def soft_delete(self) -> None:
        """Mark this record as deleted at the current UTC time."""
        self.deleted_at = datetime.now(UTC)


# ── TenantMixin ──────────────────────────────────────────────────────────────
class TenantMixin:
    """Adds a required ``tenant_id`` column for multi-tenant isolation."""

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        nullable=False,
        index=True,
    )


# ── BaseModel (combined) ─────────────────────────────────────────────────────
class BaseModel(TimestampMixin, SoftDeleteMixin, Base):
    """Abstract base that combines timestamping, soft-delete, and a UUID PK.

    The primary key uses ``gen_random_uuid()`` as server default.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=None,  # let the DB generate it when omitted
    )
