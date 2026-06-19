"""
Billing router: subscriptions, invoices, credit wallet, usage, and Stripe webhook.

All endpoints (except POST /billing/webhook) require an authenticated active
user and tenant context.  Responses use the standard ``{data, meta, links}``
envelope for lists and ``{data: {...}}`` for single resources.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.auth import User
from app.models.billing import Invoice, Subscription
from app.schemas.base import build_list_response, build_single_response
from app.schemas.billing import (
    SubscriptionCancel,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
    InvoiceResponse,
    WalletResponse,
    WalletTopUp,
    UsageRecordResponse,
    UsageSummaryResponse,
)
from app.services.billing import BillingService

router = APIRouter(prefix="/billing", tags=["billing"])


# ── Subscriptions ─────────────────────────────────────────────────────────────


@router.post("/subscriptions", status_code=201)
async def create_subscription(
    body: SubscriptionCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new subscription for the current tenant.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = BillingService(db)
    sub = await service.create_subscription(
        tenant_id=tenant_id,
        plan_tier=body.plan_tier,
        trial_days=body.trial_days,
    )
    return build_single_response(SubscriptionResponse.model_validate(sub))


@router.get("/subscriptions")
async def list_subscriptions(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List subscriptions for the current tenant.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    skip = (page - 1) * limit
    service = BillingService(db)
    items, total = await service._get_subscription_list(tenant_id, skip=skip, limit=limit)
    return build_list_response(
        data=[SubscriptionResponse.model_validate(s) for s in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/subscriptions/{subscription_id}")
async def get_subscription(
    subscription_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single subscription.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = BillingService(db)
    sub = await service._get_subscription(subscription_id, tenant_id=tenant_id)
    return build_single_response(SubscriptionResponse.model_validate(sub))


@router.patch("/subscriptions/{subscription_id}")
async def update_subscription_plan(
    subscription_id: UUID,
    body: SubscriptionUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upgrade or downgrade a subscription's plan tier.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = BillingService(db)
    sub = await service.upgrade_downgrade(
        subscription_id=subscription_id,
        new_plan_tier=body.plan_tier,
        tenant_id=tenant_id,
    )
    return build_single_response(SubscriptionResponse.model_validate(sub))


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: UUID,
    body: SubscriptionCancel,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Cancel a subscription (immediately or at period end).

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = BillingService(db)
    sub = await service.cancel_subscription(
        subscription_id=subscription_id,
        immediate=body.immediate,
        tenant_id=tenant_id,
    )
    return build_single_response(SubscriptionResponse.model_validate(sub))


# ── Invoices ──────────────────────────────────────────────────────────────────


@router.get("/invoices")
async def list_invoices(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None, max_length=32),
) -> dict:
    """List invoices for the current tenant.

    Optionally filter by ``status`` (e.g. ``pending``, ``paid``, ``past_due``).
    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    skip = (page - 1) * limit
    service = BillingService(db)
    items, total = await service._get_invoice_list(
        tenant_id, status=status, skip=skip, limit=limit
    )
    return build_list_response(
        data=[InvoiceResponse.model_validate(inv) for inv in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/invoices/{invoice_id}")
async def get_invoice(
    invoice_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single invoice.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = BillingService(db)
    inv = await service._get_invoice(invoice_id, tenant_id=tenant_id)
    return build_single_response(InvoiceResponse.model_validate(inv))


# ── Credit Wallet ─────────────────────────────────────────────────────────────


@router.get("/wallet")
async def get_wallet(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get the current tenant's credit wallet balance.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = BillingService(db)
    wallet = await service.calculate_credits(tenant_id)
    return build_single_response(wallet)


@router.post("/wallet/top-up", status_code=201)
async def top_up_wallet(
    body: WalletTopUp,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Add credits to the tenant's wallet.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = BillingService(db)
    wallet = await service.top_up_wallet(
        tenant_id=tenant_id,
        amount=body.amount,
        payment_method=body.payment_method,
    )
    return build_single_response(WalletResponse.model_validate(wallet))


# ── Usage ─────────────────────────────────────────────────────────────────────


@router.get("/usage")
async def get_usage_summary(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    subscription_id: UUID | None = Query(None),
    metric: str | None = Query(None, max_length=100),
) -> dict:
    """Get metered usage summary for the current tenant's subscription(s).

    If ``subscription_id`` is omitted the most recent active subscription is
    used.  Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = BillingService(db)

    if subscription_id is None:
        # Use the most recent active subscription
        sub = await service._get_active_subscription(tenant_id)
        if sub is None:
            return build_single_response({"metrics": [], "subscription_id": None})
        subscription_id = sub.id

    summary = await service.get_usage_summary(subscription_id, metric=metric)
    return build_single_response(
        {
            "subscription_id": str(subscription_id),
            "metrics": summary,
        }
    )


# ── Stripe Webhook (no auth) ──────────────────────────────────────────────────


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Stripe webhook receiver — no authentication required.

    Stripe signs webhook payloads with a secret; in production the signature
    should be verified.  Returns ``{status, detail}``.
    """
    # In production, verify Stripe signature here using
    # stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    body = await request.json()
    service = BillingService(db)
    result = await service.handle_stripe_webhook(body)
    return result


# ── Payment History ───────────────────────────────────────────────────────────


@router.get("/payment-history")
async def list_payment_history(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Get payment history (paid invoices) for the current tenant.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    skip = (page - 1) * limit
    service = BillingService(db)
    items, total = await service.get_payment_history(
        tenant_id=tenant_id,
        limit=limit,
        offset=skip,
    )
    return build_list_response(
        data=[
            {
                "id": str(inv.id),
                "invoice_number": inv.invoice_number,
                "amount": float(inv.amount),
                "currency": inv.currency,
                "status": inv.status,
                "paid_at": inv.paid_at.isoformat() if inv.paid_at else None,
                "created_at": inv.created_at.isoformat(),
            }
            for inv in items
        ],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )
