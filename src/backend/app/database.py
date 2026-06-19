"""
Async SQLAlchemy engine, session factory, and dependency helpers.

Provides the declarative ``Base``, an async ``engine``, and a session factory
``async_session_factory`` alongside the FastAPI dependency ``get_db``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# ── Engine ───────────────────────────────────────────────────────────────────
engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    echo=settings.debug,
)

# ── Session factory ──────────────────────────────────────────────────────────
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Declarative base ─────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all ORM models."""

    __allow_unmapped__ = False


# ── FastAPI dependency ───────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async database session.

    Usage::

        @app.get("/items")
        async def list_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    session = async_session_factory()
    try:
        yield session
    finally:
        await session.close()


# ── Tenant-aware session helper ──────────────────────────────────────────────
def set_tenant_id(session: AsyncSession, tenant_id: str) -> None:
    """Set the ``app.current_tenant_id`` session variable for Row-Level Security.

    The PostgreSQL trigger / RLS policy reads this variable to filter rows.
    """
    import sqlalchemy as sa

    session.sync_session.execute(
        sa.text("SELECT set_config('app.current_tenant_id', :tid, true)"),
        {"tid": tenant_id},
    )
