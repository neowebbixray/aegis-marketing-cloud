"""
Base service with common CRUD operations for all entity services.
"""

from __future__ import annotations

import logging
from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from sqlalchemy import Select, select, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.core.exceptions import NotFoundException
from app.database import Base

ModelT = TypeVar("ModelT", bound=Base)

logger = logging.getLogger("amc.services.base")


class BaseService(Generic[ModelT]):
    """Generic CRUD service for SQLAlchemy models.

    Provides ``get``, ``list``, ``create``, ``update``, ``soft_delete``,
    and ``restore`` methods.

    Subclasses set ``model`` to the SQLAlchemy model class and may override
    ``_apply_tenant_filter`` for multi-tenant isolation.
    """

    model: type[ModelT]

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Query helpers ────────────────────────────────────────────────────────

    def _apply_tenant_filter(
        self, stmt: Select, tenant_id: UUID | None = None
    ) -> Select:
        """Apply tenant-scoped filtering if the model has a ``tenant_id`` column.

        Override in subclasses for custom filtering logic.
        """
        if tenant_id is not None and hasattr(self.model, "tenant_id"):
            stmt = stmt.where(self.model.tenant_id == tenant_id)  # type: ignore[union-attr]
        return stmt

    def _apply_soft_delete_filter(self, stmt: Select, include_deleted: bool = False) -> Select:
        """Exclude soft-deleted rows unless *include_deleted* is ``True``."""
        if not include_deleted and hasattr(self.model, "deleted_at"):
            stmt = stmt.where(self.model.deleted_at.is_(None))  # type: ignore[union-attr]
        return stmt

    # ── CRUD ─────────────────────────────────────────────────────────────────

    async def get(
        self, id: UUID, tenant_id: UUID | None = None, include_deleted: bool = False
    ) -> ModelT:
        """Fetch a single record by primary key.

        Raises ``NotFoundException`` if not found.
        """
        stmt = select(self.model).where(self.model.id == id)  # type: ignore[union-attr]
        stmt = self._apply_tenant_filter(stmt, tenant_id)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted)
        result = await self.db.execute(stmt)
        obj = result.scalars().first()
        if obj is None:
            raise NotFoundException(detail=f"{self.model.__name__} not found")
        return obj

    async def list(
        self,
        tenant_id: UUID | None = None,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 50,
        filters: list[ColumnElement] | None = None,
        order_by: ColumnElement | None = None,
    ) -> tuple[list[ModelT], int]:
        """Fetch a paginated list of records with total count.

        Returns:
            Tuple of ``(items, total_count)``.
        """
        # Count query
        count_stmt = select(func.count()).select_from(self.model)
        count_stmt = self._apply_tenant_filter(count_stmt, tenant_id)
        count_stmt = self._apply_soft_delete_filter(count_stmt, include_deleted)
        if filters:
            for f in filters:
                count_stmt = count_stmt.where(f)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Data query
        stmt = select(self.model)
        stmt = self._apply_tenant_filter(stmt, tenant_id)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted)
        if filters:
            for f in filters:
                stmt = stmt.where(f)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def create(self, **kwargs: Any) -> ModelT:
        """Create a new record and flush to the database."""
        obj = self.model(**kwargs)
        self.db.add(obj)
        await self.db.flush()
        await self.db.refresh(obj)
        logger.debug("Created %s: %s", self.model.__name__, obj.id)
        return obj

    async def update(
        self, id: UUID, tenant_id: UUID | None = None, **kwargs: Any
    ) -> ModelT:
        """Update a record in-place. Raises ``NotFoundException`` if not found."""
        obj = await self.get(id, tenant_id=tenant_id)
        for key, value in kwargs.items():
            if value is not None or key in kwargs:
                setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        logger.debug("Updated %s: %s", self.model.__name__, id)
        return obj

    async def soft_delete(self, id: UUID, tenant_id: UUID | None = None) -> None:
        """Soft-delete a record by setting its ``deleted_at`` timestamp."""
        obj = await self.get(id, tenant_id=tenant_id)
        if hasattr(obj, "soft_delete"):
            obj.soft_delete()
        await self.db.flush()
        logger.debug("Soft-deleted %s: %s", self.model.__name__, id)

    async def restore(self, id: UUID, tenant_id: UUID | None = None) -> ModelT:
        """Restore a soft-deleted record."""
        obj = await self.get(id, tenant_id=tenant_id, include_deleted=True)
        if hasattr(obj, "restore"):
            obj.restore()
        await self.db.flush()
        logger.debug("Restored %s: %s", self.model.__name__, id)
        return obj

    async def delete_permanent(self, id: UUID) -> None:
        """Permanently delete a record (bypasses soft-delete)."""
        stmt = sa_delete(self.model).where(self.model.id == id)  # type: ignore[union-attr]
        await self.db.execute(stmt)
        await self.db.flush()
        logger.debug("Permanently deleted %s: %s", self.model.__name__, id)
