"""
Pydantic schemas for the billing module: subscriptions, invoices, credit wallets, usage records.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Plan / Tier constants ─────────────────────────────────────────────────────

PLAN_TIERS = {"free", "starter", "professional", "enterprise"}


# ── Subscription ──────────────────────────────────────────────────────────────
class SubscriptionCreate(BaseModel):
    """Payload for POST /billing/subscriptions."""

    plan_tier: str = Field(..., min_length=1, max_length=50)
    trial_days: Optional[int] = Field(None, ge=0, le=365)

    @field_validator("plan_tier")
    @classmethod
    def validate_plan_tier(cls, v: str) -> str:
        lowered = v.lower()
        if lowered not in PLAN_TIERS:
            raise ValueError(f"Invalid plan tier '{v}'. Must be one of: {', '.join(sorted(PLAN_TIERS))}")
        return lowered


class SubscriptionUpdate(BaseModel):
    """Payload for PATCH /billing/subscriptions/{id} — plan change."""

    plan_tier: str = Field(..., min_length=1, max_length=50)

    @field_validator("plan_tier")
    @classmethod
    def validate_plan_tier(cls, v: str) -> str:
        lowered = v.lower()
        if lowered not in PLAN_TIERS:
            raise ValueError(f"Invalid plan tier '{v}'. Must be one of: {', '.join(sorted(PLAN_TIERS))}")
        return lowered


class SubscriptionCancel(BaseModel):
    """Payload for POST /billing/subscriptions/{id}/cancel."""

    immediate: bool = False


class SubscriptionResponse(BaseModel):
    """Subscription representation."""

    id: UUID
    tenant_id: UUID
    plan_id: str
    status: str
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    payment_provider: Optional[str] = None
    payment_provider_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Invoice ───────────────────────────────────────────────────────────────────
class InvoiceResponse(BaseModel):
    """Invoice representation."""

    id: UUID
    tenant_id: UUID
    subscription_id: Optional[UUID] = None
    invoice_number: str
    amount: Decimal
    currency: str
    status: str
    paid_at: Optional[datetime] = None
    line_items: Optional[list[Any]] = None
    metadata: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Credit Wallet ─────────────────────────────────────────────────────────────
class WalletTopUp(BaseModel):
    """Payload for POST /billing/wallet/top-up."""

    amount: Decimal = Field(..., gt=Decimal("0"), decimal_places=2)
    payment_method: Optional[str] = Field(None, max_length=64)


class WalletResponse(BaseModel):
    """Credit wallet representation."""

    id: UUID
    tenant_id: UUID
    balance: Decimal
    lifetime_credits: Decimal
    lifetime_spend: Decimal
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Usage Records ─────────────────────────────────────────────────────────────
class UsageRecordResponse(BaseModel):
    """Metered usage record."""

    id: UUID
    subscription_id: UUID
    metric: str
    quantity: Decimal
    recorded_at: datetime
    metadata: Optional[dict[str, Any]] = None

    model_config = {"from_attributes": True}


class UsageSummaryResponse(BaseModel):
    """Aggregated usage summary per metric."""

    metric: str
    total_quantity: Decimal
    record_count: int


# ── Payment History ───────────────────────────────────────────────────────────
class PaymentHistoryResponse(BaseModel):
    """Payment record (from paid invoices)."""

    id: UUID
    invoice_number: str
    amount: Decimal
    currency: str
    status: str
    paid_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}
