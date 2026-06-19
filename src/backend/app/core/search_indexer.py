"""Search index maintenance utilities for PostgreSQL tsvector columns.

Provides helper functions to update the ``search_vector`` tsvector column on
the ``contacts``, ``deals``, and ``campaigns`` tables. These are called from
service-layer hooks when a record is created or updated.

The ``search_vector`` column is defined as a concatenation of relevant
text columns weighted to reflect field importance (A = high, B = medium,
C = low).  A database trigger (created by the Alembic migration) also
automatically keeps the tsvector in sync on row INSERT / UPDATE, so calling
these functions is only needed for bulk re-indexing or after a schema change.
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("amc.search_indexer")

# ── Weighted column assignments  ─────────────────────────────────────────────
# tsvector weights: A (high), B (medium), C (low), D (unspecified)
# We use upstream PostgreSQL `setweight()` to assign them.

CONTACT_VECTOR_COLS = {
    "A": ["first_name", "last_name"],
    "B": ["email", "company"],
    "C": ["phone", "position"],
}

DEAL_VECTOR_COLS = {
    "A": ["name"],
    "B": ["organization_label"],
}

CAMPAIGN_VECTOR_COLS = {
    "A": ["name"],
    "B": ["description", "campaign_type", "channel"],
}


def _build_tsvector_update(table: str, weight_map: dict[str, list[str]]) -> str:
    """Build a SQL expression that produces a weighted tsvector for *table*.

    Example output (condensed)::

        setweight(to_tsvector('english', coalesce(first_name, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(email, '')), 'B')
    """
    parts: list[str] = []
    for weight in ("A", "B", "C"):
        cols = weight_map.get(weight, [])
        for col in cols:
            parts.append(
                (
                    f"setweight("
                    f"to_tsvector('english', coalesce({col}, '')), '{weight}')"
                )
            )
    return " || ".join(parts)


# ── Public helpers ────────────────────────────────────────────────────────────


async def update_contact_search_index(db: AsyncSession, contact_id: UUID) -> None:
    """Update the tsvector for a single contact."""
    expr = _build_tsvector_update("contacts", CONTACT_VECTOR_COLS)
    stmt = text(
        f"UPDATE contacts SET search_vector = {expr} WHERE id = :id"
    ).bindparams(id=contact_id)
    await db.execute(stmt)
    await db.flush()
    logger.debug("Updated search index for contact %s", contact_id)


async def update_deal_search_index(db: AsyncSession, deal_id: UUID) -> None:
    """Update the tsvector for a single deal."""
    expr = _build_tsvector_update("deals", DEAL_VECTOR_COLS)
    stmt = text(
        f"UPDATE deals SET search_vector = {expr} WHERE id = :id"
    ).bindparams(id=deal_id)
    await db.execute(stmt)
    await db.flush()
    logger.debug("Updated search index for deal %s", deal_id)


async def update_campaign_search_index(db: AsyncSession, campaign_id: UUID) -> None:
    """Update the tsvector for a single campaign."""
    expr = _build_tsvector_update("campaigns", CAMPAIGN_VECTOR_COLS)
    stmt = text(
        f"UPDATE campaigns SET search_vector = {expr} WHERE id = :id"
    ).bindparams(id=campaign_id)
    await db.execute(stmt)
    await db.flush()
    logger.debug("Updated search index for campaign %s", campaign_id)


async def reindex_all(db: AsyncSession) -> dict[str, int]:
    """Rebuild the search_vector column for every row in all three tables.

    Returns a dict mapping table name to the number of rows updated.
    """
    results: dict[str, int] = {}

    for table, weight_map in (
        ("contacts", CONTACT_VECTOR_COLS),
        ("deals", DEAL_VECTOR_COLS),
        ("campaigns", CAMPAIGN_VECTOR_COLS),
    ):
        expr = _build_tsvector_update(table, weight_map)
        stmt = text(
            f"UPDATE {table} SET search_vector = {expr} "
            f"WHERE search_vector IS DISTINCT FROM ({expr})"
        )
        result = await db.execute(stmt)
        await db.flush()
        rowcount = result.rowcount if result.rowcount != -1 else 0
        results[table] = rowcount
        logger.info("Reindexed %s — %d rows updated", table, rowcount)

    await db.commit()
    return results
