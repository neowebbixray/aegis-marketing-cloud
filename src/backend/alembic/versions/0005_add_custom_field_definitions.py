"""Add custom field definitions table

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-21

Tables added:
- custom_field_definitions — stores definitions for custom fields per workspace

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create custom_field_definitions table
    op.create_table(
        "custom_field_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workspace_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("key", sa.String(64), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("field_type", sa.String(32), nullable=False),
        sa.Column("config", postgresql.JSONB, default=dict, nullable=False),
        sa.Column("is_required", sa.Boolean(), default=False, nullable=False),
        sa.Column("is_active", sa.Boolean(), default=True, nullable=False),
        sa.Column("display_order", sa.Integer(), default=0, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),

        # Composite unique key for tenant + workspace + key
        sa.UniqueConstraint("tenant_id", "workspace_id", "key", name="uq_custom_field_definition_tenant_workspace_key"),
    )

    # Create indexes
    op.create_index("ix_custom_field_definitions_tenant_id", "custom_field_definitions", ["tenant_id"])
    op.create_index("ix_custom_field_definitions_workspace_id", "custom_field_definitions", ["workspace_id"])
    op.create_index("ix_custom_field_definitions_is_active", "custom_field_definitions", ["is_active"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("ix_custom_field_definitions_is_active", table_name="custom_field_definitions")
    op.drop_index("ix_custom_field_definitions_workspace_id", table_name="custom_field_definitions")
    op.drop_index("ix_custom_field_definitions_tenant_id", table_name="custom_field_definitions")

    # Drop table
    op.drop_table("custom_field_definitions")
