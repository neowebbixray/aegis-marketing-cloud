"""
Billing service: subscriptions, invoices, credit wallets, usage recording,
Stripe webhook handling, and dunning (retry) logic.

All tenant-scoped operations require a ``tenant_id`` UUID.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.models.billing import CreditWallet, Invoice, Subscription, UsageRecord
from app.schemas.billing import PLAN_TIERS

logger = logging.getLogger("amc.services.billing")

# ── Plan pricing (simple flat-rate model) ─────────────────────────────────────
PLAN_PRICES: dict[str, Decimal] = {
    "free": Decimal("0.00"),
    "starter": Decimal("29.00"),
    "professional": Decimal("99.00"),
    "enterprise": Decimal("299.00"),
}

# Maximum dunning retry attempts
DUNNING_MAX_RETRIES = 3
DUNNING_RETRY_INTERVALS_HOURS = [1, 6, 24]  # increasing wait between retries


class BillingService:
    """High-level billing operations for a single tenant context."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Subscriptions ─────────────────────────────────────────────────────────

    async def create_subscription(
        self,
        tenant_id: UUID,
        plan_tier: str,
        trial_days: int | None = None,
    ) -> Subscription:
        """Create a new subscription for the given tenant.

        If a subscription already exists and is active, a ``ConflictException``
        is raised.  Trial days are honoured when provided.
        """
        # Ensure no active subscription already exists
        existing = await self._get_active_subscription(tenant_id)
        if existing:
            raise ConflictException(
                detail=f"Tenant {tenant_id} already has an active subscription ({existing.status})"
            )

        plan_id = plan_tier.lower()
        if plan_id not in PLAN_TIERS:
            raise ValidationException(
                detail=f"Invalid plan tier '{plan_tier}'. Must be one of: {', '.join(sorted(PLAN_TIERS))}"
            )

        now = datetime.now(timezone.utc)
        period_start = now
        period_end = now + timedelta(days=30)
        trial_end = None
        status = "active"

        if trial_days and trial_days > 0:
            trial_end = now + timedelta(days=trial_days)
            status = "trialing"

        sub = Subscription(
            tenant_id=tenant_id,
            plan_id=plan_id,
            status=status,
            current_period_start=period_start,
            current_period_end=period_end,
            trial_end=trial_end,
        )
        self.db.add(sub)
        await self.db.flush()
        await self.db.refresh(sub)

        # Ensure a credit wallet exists
        await self._ensure_wallet(tenant_id)

        logger.info("Created subscription %s for tenant %s (plan=%s)", sub.id, tenant_id, plan_id)
        return sub

    async def cancel_subscription(
        self,
        subscription_id: UUID,
        immediate: bool = False,
        tenant_id: UUID | None = None,
    ) -> Subscription:
        """Cancel a subscription.

        If *immediate* is ``True`` the subscription status is changed to
        ``cancelled`` right away.  Otherwise it is marked ``cancel_at_period_end``
        and will expire when the current period ends.
        """
        sub = await self._get_subscription(subscription_id, tenant_id)

        if sub.status in ("cancelled", "cancel_at_period_end"):
            raise ConflictException(detail=f"Subscription {subscription_id} is already cancelled")

        now = datetime.now(timezone.utc)
        if immediate:
            sub.status = "cancelled"
            sub.cancelled_at = now
        else:
            sub.status = "cancel_at_period_end"

        await self.db.flush()
        await self.db.refresh(sub)
        logger.info(
            "Subscription %s cancelled (immediate=%s)", subscription_id, immediate
        )
        return sub

    async def upgrade_downgrade(
        self,
        subscription_id: UUID,
        new_plan_tier: str,
        tenant_id: UUID | None = None,
    ) -> Subscription:
        """Change the plan tier on an existing subscription.

        Upgrades take effect immediately (prorated); downgrades are scheduled
        for the next billing period.
        """
        sub = await self._get_subscription(subscription_id, tenant_id)
        plan_id = new_plan_tier.lower()

        if plan_id not in PLAN_TIERS:
            raise ValidationException(
                detail=f"Invalid plan tier '{new_plan_tier}'. Must be one of: {', '.join(sorted(PLAN_TIERS))}"
            )

        if sub.status not in ("active", "trialing", "cancel_at_period_end"):
            raise ValidationException(
                detail=f"Cannot change plan on subscription in status '{sub.status}'"
            )

        old_plan = sub.plan_id
        new_price = PLAN_PRICES.get(plan_id, Decimal("0"))
        old_price = PLAN_PRICES.get(old_plan, Decimal("0"))

        if new_price > old_price:
            # Upgrade — immediate
            sub.plan_id = plan_id
            logger.info(
                "Subscription %s upgraded from %s to %s (immediate)",
                subscription_id,
                old_plan,
                plan_id,
            )
        else:
            # Downgrade — schedule for next period
            sub.plan_id = plan_id
            logger.info(
                "Subscription %s downgraded from %s to %s (next period)",
                subscription_id,
                old_plan,
                plan_id,
            )

        await self.db.flush()
        await self.db.refresh(sub)
        return sub

    # ── Invoices ──────────────────────────────────────────────────────────────

    async def generate_invoice(
        self,
        tenant_id: UUID,
        period_start: datetime | None = None,
        period_end: datetime | None = None,
    ) -> Invoice:
        """Generate an invoice for a tenant for the given billing period.

        The invoice amount is derived from the tenant's active subscription
        plan price.  Usage-based overages are included from ``UsageRecord``
        entries for the period.
        """
        sub = await self._get_active_subscription(tenant_id)
        if not sub:
            raise NotFoundException(detail="No active subscription found for tenant")

        now = datetime.now(timezone.utc)
        p_start = period_start or sub.current_period_start or now
        p_end = period_end or sub.current_period_end or (now + timedelta(days=30))

        base_amount = PLAN_PRICES.get(sub.plan_id, Decimal("0"))

        # Gather usage-based charges for the period
        usage_result = await self.db.execute(
            select(
                UsageRecord.metric,
                func.sum(UsageRecord.quantity).label("total_qty"),
            )
            .where(
                and_(
                    UsageRecord.subscription_id == sub.id,
                    UsageRecord.recorded_at >= p_start,
                    UsageRecord.recorded_at <= p_end,
                )
            )
            .group_by(UsageRecord.metric)
        )
        usage_rows = usage_result.all()
        usage_charges = Decimal("0")
        line_items: list[dict[str, Any]] = [
            {
                "description": f"{sub.plan_id.title()} plan — base fee",
                "amount": float(base_amount),
                "quantity": 1,
                "total": float(base_amount),
            }
        ]
        for row in usage_rows:
            # Simple overage pricing: $0.10 per unit
            metric_total = Decimal(str(row.total_qty)) * Decimal("0.10")
            usage_charges += metric_total
            line_items.append(
                {
                    "description": f"Metered usage — {row.metric}",
                    "amount": float(metric_total),
                    "quantity": float(row.total_qty),
                    "total": float(metric_total),
                }
            )

        total_amount = base_amount + usage_charges
        invoice_number = f"INV-{now.strftime('%Y%m')}-{uuid4().hex[:8].upper()}"

        inv = Invoice(
            tenant_id=tenant_id,
            subscription_id=sub.id,
            invoice_number=invoice_number,
            amount=total_amount,
            currency="USD",
            status="pending",
            line_items=line_items,
        )
        self.db.add(inv)
        await self.db.flush()
        await self.db.refresh(inv)

        logger.info(
            "Generated invoice %s for tenant %s ($%.2f)",
            invoice_number,
            tenant_id,
            total_amount,
        )
        return inv

    # ── Usage Recording ───────────────────────────────────────────────────────

    async def record_usage(
        self,
        subscription_id: UUID,
        metric: str,
        quantity: Decimal,
        metadata: dict[str, Any] | None = None,
    ) -> UsageRecord:
        """Record a metered usage event against a subscription."""
        sub = await self._get_subscription(subscription_id)
        if sub.status not in ("active", "trialing"):
            raise ValidationException(
                detail=f"Cannot record usage for subscription in status '{sub.status}'"
            )

        record = UsageRecord(
            subscription_id=subscription_id,
            metric=metric,
            quantity=quantity,
            recorded_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        logger.debug("Recorded usage %s=%.4f for subscription %s", metric, quantity, subscription_id)
        return record

    # ── Credit Wallet ─────────────────────────────────────────────────────────

    async def calculate_credits(
        self,
        tenant_id: UUID,
        feature: str | None = None,
    ) -> dict[str, Any]:
        """Return the current credit wallet balance and optional feature cost.

        Returns a dict with ``balance``, ``lifetime_credits``, ``lifetime_spend``,
        and if *feature* is provided, an estimate of how many operations the
        balance can cover (assuming $0.01 per operation).
        """
        wallet = await self._get_wallet(tenant_id)
        result: dict[str, Any] = {
            "balance": wallet.balance,
            "lifetime_credits": wallet.lifetime_credits,
            "lifetime_spend": wallet.lifetime_spend,
        }
        if feature:
            # Assume $0.01 per operation as a simplistic cost model
            cost_per_op = Decimal("0.01")
            if cost_per_op > 0 and wallet.balance > 0:
                result["remaining_operations"] = int(wallet.balance / cost_per_op)
            else:
                result["remaining_operations"] = 0
            result["cost_per_op"] = cost_per_op
        return result

    async def top_up_wallet(
        self,
        tenant_id: UUID,
        amount: Decimal,
        payment_method: str | None = None,
    ) -> CreditWallet:
        """Add credits to the wallet.

        This simulates a payment flow — in production it would integrate with
        a payment provider (Stripe, etc.).
        """
        if amount <= 0:
            raise ValidationException(detail="Top-up amount must be positive")

        wallet = await self._ensure_wallet(tenant_id)
        wallet.balance += amount
        wallet.lifetime_credits += amount
        await self.db.flush()
        await self.db.refresh(wallet)

        logger.info(
            "Wallet top-up for tenant %s: +$%.2f (balance=$%.2f)",
            tenant_id,
            amount,
            wallet.balance,
        )
        return wallet

    # ── Payment History ───────────────────────────────────────────────────────

    async def get_payment_history(
        self,
        tenant_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Invoice], int]:
        """Return paid invoices as payment history, newest first."""
        stmt = (
            select(Invoice)
            .where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.status.in_(["paid", "completed"]),
                )
            )
            .order_by(desc(Invoice.paid_at), desc(Invoice.created_at))
            .offset(offset)
            .limit(limit)
        )
        count_stmt = (
            select(func.count())
            .select_from(Invoice)
            .where(
                and_(
                    Invoice.tenant_id == tenant_id,
                    Invoice.status.in_(["paid", "completed"]),
                )
            )
        )
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    # ── Dunning (retry) ───────────────────────────────────────────────────────

    async def dunning_process(self, failed_invoice_id: UUID) -> dict[str, Any]:
        """Execute dunning retry logic for a failed invoice.

        Checks how many retries have already been attempted (stored in
        invoice ``metadata``) and either schedules a retry or marks the
        invoice as ``failed`` permanently.

        Returns a dict with the outcome.
        """
        inv = await self.db.get(Invoice, failed_invoice_id)
        if inv is None:
            raise NotFoundException(detail=f"Invoice {failed_invoice_id} not found")

        metadata = inv.metadata or {}
        retries = metadata.get("dunning_retries", 0)

        if retries >= DUNNING_MAX_RETRIES:
            # Max retries exhausted — mark as permanently failed
            inv.status = "failed"
            await self.db.flush()
            logger.warning(
                "Dunning exhausted for invoice %s after %d retries",
                failed_invoice_id,
                retries,
            )
            return {
                "status": "failed",
                "invoice_id": str(failed_invoice_id),
                "retries": retries,
                "detail": "Max retries exhausted. Invoice marked as failed.",
            }

        # Calculate next retry interval
        interval_hours = DUNNING_RETRY_INTERVALS_HOURS[
            min(retries, len(DUNNING_RETRY_INTERVALS_HOURS) - 1)
        ]
        next_retry_at = datetime.now(timezone.utc) + timedelta(hours=interval_hours)

        metadata["dunning_retries"] = retries + 1
        metadata["next_retry_at"] = next_retry_at.isoformat()
        metadata["last_retry_at"] = datetime.now(timezone.utc).isoformat()
        inv.metadata = metadata

        # Reset to pending so a background worker can retry
        inv.status = "pending"
        await self.db.flush()

        logger.info(
            "Dunning retry #%d for invoice %s scheduled in %d hour(s)",
            retries + 1,
            failed_invoice_id,
            interval_hours,
        )
        return {
            "status": "pending",
            "invoice_id": str(failed_invoice_id),
            "retries": retries + 1,
            "next_retry_at": next_retry_at.isoformat(),
            "detail": f"Retry #{retries + 1} scheduled in {interval_hours} hour(s).",
        }

    # ── Stripe Webhook ────────────────────────────────────────────────────────

    async def handle_stripe_webhook(self, event: dict[str, Any]) -> dict[str, Any]:
        """Process an incoming Stripe webhook event.

        Supported event types:
        - ``invoice.paid`` / ``invoice.payment_succeeded``
        - ``invoice.payment_failed``
        - ``customer.subscription.updated``
        - ``customer.subscription.deleted``
        - ``customer.subscription.trial_will_end``

        Returns a dict describing the action taken.
        """
        event_type = event.get("type", "")
        data_object = event.get("data", {}).get("object", {})

        logger.info("Processing Stripe webhook event: %s", event_type)

        if event_type in ("invoice.paid", "invoice.payment_succeeded"):
            return await self._handle_invoice_paid(data_object)
        elif event_type == "invoice.payment_failed":
            return await self._handle_invoice_payment_failed(data_object)
        elif event_type == "customer.subscription.updated":
            return await self._handle_subscription_updated(data_object)
        elif event_type == "customer.subscription.deleted":
            return await self._handle_subscription_deleted(data_object)
        elif event_type == "customer.subscription.trial_will_end":
            return {"status": "acknowledged", "detail": "Trial ending notification received."}
        else:
            logger.debug("Unhandled Stripe event type: %s", event_type)
            return {"status": "ignored", "detail": f"Unhandled event type: {event_type}"}

    async def _handle_invoice_paid(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Mark local invoice as paid when Stripe confirms payment."""
        stripe_invoice_id = obj.get("id")
        # Match via payment_provider_id on subscription or metadata on invoice
        subscription_id = obj.get("subscription")
        if subscription_id:
            result = await self.db.execute(
                select(Subscription).where(
                    Subscription.payment_provider_id == subscription_id
                )
            )
            sub = result.scalars().first()
            if sub:
                # Find the matching invoice
                inv_result = await self.db.execute(
                    select(Invoice)
                    .where(
                        and_(
                            Invoice.subscription_id == sub.id,
                            Invoice.status == "pending",
                        )
                    )
                    .order_by(desc(Invoice.created_at))
                    .limit(1)
                )
                inv = inv_result.scalars().first()
                if inv:
                    inv.status = "paid"
                    inv.paid_at = datetime.now(timezone.utc)
                    await self.db.flush()
                    logger.info("Invoice %s marked as paid (Stripe)", inv.invoice_number)
                    return {"status": "paid", "invoice_id": str(inv.id)}
        return {"status": "acknowledged", "detail": f"Invoice {stripe_invoice_id} paid (no local match)"}

    async def _handle_invoice_payment_failed(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Handle a failed payment notification from Stripe."""
        stripe_invoice_id = obj.get("id")
        subscription_id = obj.get("subscription")
        if subscription_id:
            result = await self.db.execute(
                select(Subscription).where(
                    Subscription.payment_provider_id == subscription_id
                )
            )
            sub = result.scalars().first()
            if sub:
                inv_result = await self.db.execute(
                    select(Invoice)
                    .where(
                        and_(
                            Invoice.subscription_id == sub.id,
                            Invoice.status == "pending",
                        )
                    )
                    .order_by(desc(Invoice.created_at))
                    .limit(1)
                )
                inv = inv_result.scalars().first()
                if inv:
                    inv.status = "past_due"
                    await self.db.flush()
                    # Kick off dunning
                    dunning_result = await self.dunning_process(inv.id)
                    logger.info("Invoice %s past due, dunning started", inv.invoice_number)
                    return dunning_result
        return {"status": "acknowledged", "detail": f"Payment failed for {stripe_invoice_id}"}

    async def _handle_subscription_updated(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Sync subscription changes from Stripe."""
        stripe_sub_id = obj.get("id")
        status = obj.get("status")
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.payment_provider_id == stripe_sub_id
            )
        )
        sub = result.scalars().first()
        if sub and status:
            sub.status = status
            await self.db.flush()
            logger.info("Subscription %s status synced to '%s' from Stripe", sub.id, status)
            return {"status": "synced", "subscription_id": str(sub.id)}
        return {"status": "acknowledged", "detail": f"No local subscription for {stripe_sub_id}"}

    async def _handle_subscription_deleted(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Cancel local subscription when Stripe deletes it."""
        stripe_sub_id = obj.get("id")
        result = await self.db.execute(
            select(Subscription).where(
                Subscription.payment_provider_id == stripe_sub_id
            )
        )
        sub = result.scalars().first()
        if sub:
            sub.status = "cancelled"
            sub.cancelled_at = datetime.now(timezone.utc)
            await self.db.flush()
            logger.info("Subscription %s cancelled via Stripe webhook", sub.id)
            return {"status": "cancelled", "subscription_id": str(sub.id)}
        return {"status": "acknowledged", "detail": f"No local subscription for {stripe_sub_id}"}

    # ── Usage Summary ─────────────────────────────────────────────────────────

    async def get_usage_summary(
        self,
        subscription_id: UUID,
        metric: str | None = None,
    ) -> list[dict[str, Any]]:
        """Return aggregated usage per metric for a subscription."""
        filters = [UsageRecord.subscription_id == subscription_id]
        if metric:
            filters.append(UsageRecord.metric == metric)

        stmt = (
            select(
                UsageRecord.metric,
                func.sum(UsageRecord.quantity).label("total_quantity"),
                func.count(UsageRecord.id).label("record_count"),
            )
            .where(and_(*filters))
            .group_by(UsageRecord.metric)
            .order_by(UsageRecord.metric)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        return [
            {
                "metric": row.metric,
                "total_quantity": float(row.total_quantity),
                "record_count": row.record_count,
            }
            for row in rows
        ]

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get_subscription_list(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Subscription], int]:
        """Paginated list of subscriptions for a tenant (newest first)."""
        count_stmt = (
            select(func.count())
            .select_from(Subscription)
            .where(Subscription.tenant_id == tenant_id)
        )
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = (
            select(Subscription)
            .where(Subscription.tenant_id == tenant_id)
            .order_by(desc(Subscription.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def _get_invoice_list(
        self,
        tenant_id: UUID,
        status: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Invoice], int]:
        """Paginated list of invoices for a tenant, optionally filtered by status."""
        filters = [Invoice.tenant_id == tenant_id]
        if status:
            filters.append(Invoice.status == status)

        count_stmt = select(func.count()).select_from(Invoice).where(and_(*filters))
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = (
            select(Invoice)
            .where(and_(*filters))
            .order_by(desc(Invoice.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def _get_invoice(
        self, invoice_id: UUID, tenant_id: UUID | None = None
    ) -> Invoice:
        """Fetch a single invoice by ID, optionally tenant-scoped."""
        stmt = select(Invoice).where(Invoice.id == invoice_id)
        if tenant_id:
            stmt = stmt.where(Invoice.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        inv = result.scalars().first()
        if inv is None:
            raise NotFoundException(detail=f"Invoice {invoice_id} not found")
        return inv

    async def _get_subscription(
        self, subscription_id: UUID, tenant_id: UUID | None = None
    ) -> Subscription:
        """Fetch a subscription by ID, optionally scoped to a tenant."""
        stmt = select(Subscription).where(Subscription.id == subscription_id)
        if tenant_id:
            stmt = stmt.where(Subscription.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        sub = result.scalars().first()
        if sub is None:
            raise NotFoundException(detail=f"Subscription {subscription_id} not found")
        return sub

    async def _get_active_subscription(
        self, tenant_id: UUID
    ) -> Subscription | None:
        """Return the active/trialing subscription for a tenant, if any."""
        result = await self.db.execute(
            select(Subscription).where(
                and_(
                    Subscription.tenant_id == tenant_id,
                    Subscription.status.in_(["active", "trialing", "cancel_at_period_end"]),
                )
            )
        )
        return result.scalars().first()

    async def _ensure_wallet(self, tenant_id: UUID) -> CreditWallet:
        """Return the existing wallet or create one."""
        result = await self.db.execute(
            select(CreditWallet).where(CreditWallet.tenant_id == tenant_id)
        )
        wallet = result.scalars().first()
        if wallet is None:
            wallet = CreditWallet(tenant_id=tenant_id)
            self.db.add(wallet)
            await self.db.flush()
            await self.db.refresh(wallet)
        return wallet

    async def _get_wallet(self, tenant_id: UUID) -> CreditWallet:
        """Fetch the wallet, raising if not found."""
        wallet = await self._ensure_wallet(tenant_id)
        return wallet
