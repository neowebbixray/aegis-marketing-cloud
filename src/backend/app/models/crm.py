"""
SQLAlchemy models for the CRM module: Contact, Deal, Pipeline, PipelineStage,
and Activity.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, SoftDeleteMixin


class Contact(BaseModel, SoftDeleteMixin):
    """Customer / lead / contact record."""

    __tablename__ = "contacts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    lifecycle_stage: Mapped[str] = mapped_column(
        String(32), default="lead", nullable=False
    )  # lead, qualified, opportunity, customer, churned
    source: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    custom_fields: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, default=dict, nullable=True
    )
    tags: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text), default=list, nullable=True
    )
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Contact {self.first_name} {self.last_name}>"


class Pipeline(BaseModel, SoftDeleteMixin):
    """Sales pipeline / funnel definition."""

    __tablename__ = "pipelines"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    stages: Mapped[list["PipelineStage"]] = relationship(
        "PipelineStage",
        back_populates="pipeline",
        cascade="all, delete-orphan",
        order_by="PipelineStage.order",
    )
    deals: Mapped[list["Deal"]] = relationship(
        "Deal", back_populates="pipeline", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Pipeline {self.name}>"


class PipelineStage(BaseModel):
    """A stage within a pipeline."""

    __tablename__ = "pipeline_stages"

    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    probability: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # win probability 0-100
    colour: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)  # hex colour

    # Relationships
    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="stages")

    def __repr__(self) -> str:
        return f"<PipelineStage {self.name} (order={self.order})>"


class Deal(BaseModel, SoftDeleteMixin):
    """Sales opportunity / deal record."""

    __tablename__ = "deals"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    value: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    pipeline_stage_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("pipeline_stages.id", ondelete="RESTRICT"), nullable=False
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    organization_label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    owner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    custom_fields: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB, default=dict, nullable=True
    )

    # Relationships
    pipeline_stage: Mapped["PipelineStage"] = relationship("PipelineStage")
    pipeline: Mapped["Pipeline"] = relationship(
        "Pipeline",
        primaryjoin="Deal.pipeline_stage_id == PipelineStage.id",
        secondary="pipeline_stages",
        secondaryjoin="PipelineStage.pipeline_id == Pipeline.id",
        viewonly=True,
    )

    def __repr__(self) -> str:
        return f"<Deal {self.name} (${self.value})>"


class Activity(BaseModel, SoftDeleteMixin):
    """Activity / engagement record associated with contacts and deals."""

    __tablename__ = "activities"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    workspace_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # note, call, email, meeting, task
    subject: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True
    )
    deal_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("deals.id", ondelete="SET NULL"), nullable=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Activity {self.type}: {self.subject}>"
