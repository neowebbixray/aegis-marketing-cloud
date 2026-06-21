"""
SQLAlchemy models for CRM:
Contact, Deal, Pipeline, PipelineStage, Activity, CustomFieldDefinition, LeadScoreHistory.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin, TimestampMixin


# ── Contact ──────────────────────────────────────────────────────────────────


class Contact(BaseModel, SoftDeleteMixin):
    """A contact/person record in the CRM."""

    __tablename__ = "contacts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    company: Mapped[str | None] = mapped_column(String(256), nullable=True)
    position: Mapped[str | None] = mapped_column(String(256), nullable=True)
    lifecycle_stage: Mapped[str] = mapped_column(
        String(32), default="lead", nullable=False
    )
    source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    custom_fields: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, default=dict, nullable=True
    )
    tags: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), default=list, nullable=True
    )
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    # Lead scoring fields (added via 0006 migration)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="0-100 lead score")
    score_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Timestamp when score was last updated",
    )
    # Full-text search vector (added via 0004 migration)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, nullable=True, comment="Full-text search vector"
    )

    # Relationships
    deals: Mapped[list[Deal]] = relationship("Deal", back_populates="contact", passive_deletes=True)
    activities: Mapped[list[Activity]] = relationship(
        "Activity", back_populates="contact", passive_deletes=True
    )
    lead_score_history: Mapped[list[LeadScoreHistory]] = relationship(
        "LeadScoreHistory", back_populates="contact", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Contact {self.first_name} {self.last_name}>"


# ── Pipeline ────────────────────────────────────────────────────────────────


class Pipeline(BaseModel, SoftDeleteMixin):
    """A sales pipeline with ordered stages."""

    __tablename__ = "pipelines"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    stages: Mapped[list[PipelineStage]] = relationship(
        "PipelineStage", back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="PipelineStage.order",
    )

    def __repr__(self) -> str:
        return f"<Pipeline {self.name}>"


# ── PipelineStage ───────────────────────────────────────────────────────────


class PipelineStage(BaseModel):
    """A single stage within a pipeline."""

    __tablename__ = "pipeline_stages"

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    probability: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    colour: Mapped[str | None] = mapped_column(String(7), nullable=True)

    # Relationships
    pipeline: Mapped[Pipeline] = relationship("Pipeline", back_populates="stages")

    def __repr__(self) -> str:
        return f"<PipelineStage {self.name} (pipeline={self.pipeline_id})>"


# ── Deal ────────────────────────────────────────────────────────────────────


class Deal(BaseModel):
    """Deal/opportunity in a pipeline."""

    __tablename__ = "deals"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric(12, 2), default=0, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    pipeline_stage_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("pipeline_stages.id", ondelete="RESTRICT"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    organization_label: Mapped[str | None] = mapped_column(String(256), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    probability: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)  # 0-100
    expected_close_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    custom_fields: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, default=dict, nullable=True
    )
    # Win/Loss tracking fields
    lost_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    lost_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    won_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    won_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Full-text search vector (added via 0004 migration)
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, nullable=True, comment="Full-text search vector"
    )

    # Relationships
    contact: Mapped[Contact | None] = relationship("Contact", back_populates="deals")
    activities: Mapped[list[Activity]] = relationship(
        "Activity", back_populates="deal", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Deal {self.name} ({self.value} {self.currency})>"


# ── Activity ────────────────────────────────────────────────────────────────


class Activity(BaseModel, SoftDeleteMixin):
    """A tracked activity (call, email, meeting, note, etc.) linked to a contact and/or deal."""

    __tablename__ = "activities"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(16), nullable=False, comment="call, email, meeting, task, note, etc."
    )
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )
    deal_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("deals.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    contact: Mapped[Contact | None] = relationship("Contact", back_populates="activities")
    deal: Mapped[Deal | None] = relationship("Deal", back_populates="activities")

    def __repr__(self) -> str:
        return f"<Activity {self.type}: {self.subject}>"


# ── CustomFieldDefinition ───────────────────────────────────────────────────


class CustomFieldDefinition(BaseModel, SoftDeleteMixin):
    """Custom field definition for contacts/workspace."""

    __tablename__ = "custom_field_definitions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)  # Field label
    key: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)  # API key/field name
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_type: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # text, number, date, dropdown, multi_select, url
    config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, default=dict, nullable=True
    )  # For dropdown options, validation rules, etc.
    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<CustomFieldDefinition {self.name} ({self.key})>"


# ── LeadScoreHistory ────────────────────────────────────────────────────────


class LeadScoreHistory(BaseModel):
    """Historical record of lead scores for tracking score changes over time."""

    __tablename__ = "crm_lead_scores"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)  # 0-100 score
    score_source: Mapped[str] = mapped_column(
        String(32), nullable=False, default="manual"
    )  # ai, rule_based, manual, etc.
    scoring_factors: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True
    )  # Factors that contributed to the score
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )  # AI agent or rule set that generated the score

    # Relationships
    contact: Mapped[Contact] = relationship("Contact", back_populates="lead_score_history")

    def __repr__(self) -> str:
        return f"<LeadScoreHistory contact_id={self.contact_id} score={self.score} source={self.score_source}>"
