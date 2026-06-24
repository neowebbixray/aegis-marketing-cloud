"""Add lead score fields to contacts and lead score history table

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-21

Changes:
- Add score and score_updated_at columns to contacts table
- Add crm_lead_scores table for lead score history

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add score fields to contacts table
    op.add_column(
        "contacts",
        sa.Column(
            "score",
            sa.Integer(),
            nullable=True,
            comment="0-100 lead score",
        ),
    )
    op.add_column(
        "contacts",
        sa.Column(
            "score_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when score was last updated",
        ),
    )

    # Create lead score history table
    op.create_table(
        "crm_lead_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("contact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("score_source", sa.String(32), nullable=False, server_default="manual"),
        sa.Column("scoring_factors", postgresql.JSONB, nullable=True),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),

        # Foreign key constraints
        sa.ForeignKeyConstraint(["contact_id"], ["contacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),

        # Indexes
        sa.Index("ix_crm_lead_scores_contact_id", "contact_id"),
        sa.Index("ix_crm_lead_scores_score", "score"),
        sa.Index("ix_crm_lead_scores_score_source", "score_source"),
        sa.Index("ix_crm_lead_scores_created_at", "created_at"),
    )


def downgrade() -> None:
    # Drop lead score history table
    op.drop_table("crm_lead_scores")

    # Remove score fields from contacts table
    op.drop_column("contacts", "score_updated_at")
    op.drop_column("contacts", "score")
