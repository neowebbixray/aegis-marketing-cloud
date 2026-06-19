"""Add tsvector columns for full-text search on contacts, deals, campaigns.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-19

Tables modified:
- contacts       — adds ``search_vector`` (tsvector), GIN index, auto-update trigger
- deals          — adds ``search_vector`` (tsvector), GIN index, auto-update trigger
- campaigns      — adds ``search_vector`` (tsvector), GIN index, auto-update trigger

A custom trigger function ``amc_tsvector_update()`` is created to produce
a weighted tsvector using ``setweight()``:
- **A** (high): name / first_name + last_name
- **B** (medium): email, company, description, campaign_type, channel
- **C** (low): phone, position
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ── Trigger function ───────────────────────────────────────────────────────────


def _create_trigger_function() -> None:
    """Create a custom trigger function for weighted tsvector updates.

    This function is table-agnostic and uses ``TG_TABLE_NAME`` to dispatch
    to the correct column-to-vector mapping for each table.
    """
    op.execute(
        """
        CREATE OR REPLACE FUNCTION amc_tsvector_update()
        RETURNS trigger AS $$
        DECLARE
            v_tsv tsvector;
        BEGIN
            v_tsv := '':tsvector;

            IF TG_TABLE_NAME = 'contacts' THEN
                -- Weight A: first_name + last_name
                IF NEW.first_name IS NOT NULL OR NEW.last_name IS NOT NULL THEN
                    v_tsv := v_tsv ||
                        setweight(to_tsvector('english', coalesce(NEW.first_name, '') || ' ' || coalesce(NEW.last_name, '')), 'A');
                END IF;
                -- Weight B: email, company
                v_tsv := v_tsv || setweight(to_tsvector('english', coalesce(NEW.email, '')), 'B');
                v_tsv := v_tsv || setweight(to_tsvector('english', coalesce(NEW.company, '')), 'B');
                -- Weight C: phone, position
                v_tsv := v_tsv || setweight(to_tsvector('english', coalesce(NEW.phone, '')), 'C');
                v_tsv := v_tsv || setweight(to_tsvector('english', coalesce(NEW.position, '')), 'C');

            ELSIF TG_TABLE_NAME = 'deals' THEN
                -- Weight A: name
                v_tsv := v_tsv || setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A');
                -- Weight B: organization_label
                v_tsv := v_tsv || setweight(to_tsvector('english', coalesce(NEW.organization_label, '')), 'B');

            ELSIF TG_TABLE_NAME = 'campaigns' THEN
                -- Weight A: name
                v_tsv := v_tsv || setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A');
                -- Weight B: description, campaign_type, channel
                v_tsv := v_tsv || setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
                v_tsv := v_tsv || setweight(to_tsvector('english', coalesce(NEW.campaign_type, '')), 'B');
                v_tsv := v_tsv || setweight(to_tsvector('english', coalesce(NEW.channel, '')), 'B');
            END IF;

            NEW.search_vector := v_tsv;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def _create_contacts_trigger() -> None:
    """Create a trigger that updates contacts.search_vector on row change."""
    op.execute(
        """
        CREATE TRIGGER trg_contacts_search_vector
        BEFORE INSERT OR UPDATE OF first_name, last_name, email, company, phone, position
        ON contacts
        FOR EACH ROW
        EXECUTE FUNCTION amc_tsvector_update()
        """
    )


def _create_deals_trigger() -> None:
    """Create a trigger that updates deals.search_vector on row change."""
    op.execute(
        """
        CREATE TRIGGER trg_deals_search_vector
        BEFORE INSERT OR UPDATE OF name, organization_label
        ON deals
        FOR EACH ROW
        EXECUTE FUNCTION amc_tsvector_update()
        """
    )


def _create_campaigns_trigger() -> None:
    """Create a trigger that updates campaigns.search_vector on row change."""
    op.execute(
        """
        CREATE TRIGGER trg_campaigns_search_vector
        BEFORE INSERT OR UPDATE OF name, description, campaign_type, channel
        ON campaigns
        FOR EACH ROW
        EXECUTE FUNCTION amc_tsvector_update()
        """
    )


def _populate_contacts() -> None:
    """Set search_vector for existing contact rows by invoking the trigger."""
    op.execute(
        """
        UPDATE contacts
        SET search_vector = (
            SELECT
                setweight(to_tsvector('english', coalesce(first_name, '') || ' ' || coalesce(last_name, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(email, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(company, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(phone, '')), 'C') ||
                setweight(to_tsvector('english', coalesce(position, '')), 'C')
        )
        WHERE search_vector IS NULL
        """
    )


def _populate_deals() -> None:
    """Set search_vector for existing deal rows."""
    op.execute(
        """
        UPDATE deals
        SET search_vector = (
            SELECT
                setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(organization_label, '')), 'B')
        )
        WHERE search_vector IS NULL
        """
    )


def _populate_campaigns() -> None:
    """Set search_vector for existing campaign rows."""
    op.execute(
        """
        UPDATE campaigns
        SET search_vector = (
            SELECT
                setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(description, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(campaign_type, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(channel, '')), 'B')
        )
        WHERE search_vector IS NULL
        """
    )


# ── Migration ──────────────────────────────────────────────────────────────────


def upgrade() -> None:
    # 1. Create the custom trigger function
    _create_trigger_function()

    # 2. Add tsvector columns
    op.add_column(
        "contacts",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR,
            nullable=True,
            comment="Full-text search vector (weighted: A=name, B=email/company, C=phone/position)",
        ),
    )
    op.add_column(
        "deals",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR,
            nullable=True,
            comment="Full-text search vector (weighted: A=name, B=organization_label)",
        ),
    )
    op.add_column(
        "campaigns",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR,
            nullable=True,
            comment="Full-text search vector (weighted: A=name, B=description/type/channel)",
        ),
    )

    # 3. Create GIN indexes on the tsvector columns
    op.create_index(
        "ix_contacts_search_vector",
        "contacts",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_deals_search_vector",
        "deals",
        ["search_vector"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_campaigns_search_vector",
        "campaigns",
        ["search_vector"],
        postgresql_using="gin",
    )

    # 4. Create per-table triggers
    _create_contacts_trigger()
    _create_deals_trigger()
    _create_campaigns_trigger()

    # 5. Populate existing rows
    _populate_contacts()
    _populate_deals()
    _populate_campaigns()


def downgrade() -> None:
    # 1. Drop per-table triggers
    op.execute("DROP TRIGGER IF EXISTS trg_contacts_search_vector ON contacts")
    op.execute("DROP TRIGGER IF EXISTS trg_deals_search_vector ON deals")
    op.execute("DROP TRIGGER IF EXISTS trg_campaigns_search_vector ON campaigns")

    # 2. Drop GIN indexes
    op.drop_index("ix_contacts_search_vector", table_name="contacts")
    op.drop_index("ix_deals_search_vector", table_name="deals")
    op.drop_index("ix_campaigns_search_vector", table_name="campaigns")

    # 3. Drop tsvector columns
    op.drop_column("contacts", "search_vector")
    op.drop_column("deals", "search_vector")
    op.drop_column("campaigns", "search_vector")

    # 4. Drop the trigger function (optional — no other objects depend on it)
    op.execute("DROP FUNCTION IF EXISTS amc_tsvector_update()")
