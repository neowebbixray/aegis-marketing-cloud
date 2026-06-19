"""Billing models — subscriptions, invoices, credit wallets.

Tenant-scoped: each tenant has its own subscription and billing.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel, SoftDeleteMixin


class Subscription(BaseModel, SoftDeleteMixin):
    """Tenant subscription / billing plan."""

    __tablename__ = "subscriptions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="inactive")
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payment_provider_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def __repr__(self) -> str:
        return f"<Subscription {self.tenant_id} ({self.status})>"


class Invoice(BaseModel):
    """Invoice record for a subscription billing cycle."""

    __tablename__ = "invoices"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True
    )
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[str] = mapped_column(String(50), default="pending")
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    line_items: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True, default=list)
    metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True, default=dict)

    def __repr__(self) -> str:
        return f"<Invoice {self.invoice_number}>"


class CreditWallet(BaseModel):
    """Pre-paid credit / token balance for a tenant."""

    __tablename__ = "credit_wallets"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    lifetime_credits: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    lifetime_spend: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)

    def __repr__(self) -> str:
        return f"<CreditWallet {self.tenant_id}: ${self.balance}>"
