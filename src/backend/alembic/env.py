"""Alembic environment configuration for Aegis Marketing Cloud.

Loads the async SQLAlchemy engine from ``app.database`` and configures
Alembic to auto-detect model changes via ``app.models``.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic Config object, which provides access to values within the .ini file
config = context.config

# Set up Python logging from the Alembic config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the declarative Base so Alembic can detect models
from app import models  # noqa: F401, E402 — force model registration
from app.database import Base  # noqa: E402

target_metadata = Base.metadata


def get_database_url() -> str:
    """Return the database URL from application settings.

    Falls back to the Alembic ini placeholder if settings are not loaded.
    """
    try:
        from app.config import settings

        return settings.database_url
    except Exception:
        url = config.get_main_option("sqlalchemy.url")
        if url and "placeholder" not in url:
            return url
        raise RuntimeError(
            "DATABASE_URL must be set in the environment or config. "
            "Example: DATABASE_URL=postgresql+asyncpg://amc:secret@localhost:5432/aegis_marketing_cloud",
        ) from None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine. Calls to
    ``context.execute()`` emit the given SQL string to the script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations against the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using the async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    Uses the async engine from ``app.database``.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
