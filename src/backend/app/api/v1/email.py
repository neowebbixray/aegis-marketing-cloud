"""Email Delivery API router — send, bulk, templates, deliveries, and webhooks.

All endpoints require authentication and tenant context.
"""
from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.auth import User
from app.schemas.base import build_list_response, build_single_response
from app.schemas.email import (
    BounceWebhookPayload,
    CampaignResponse,
    DeliveryResponse,
    EmailTemplateCreate,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    SendBulkRequest,
    SendBulkResponse,
    SendRequest,
    SendResponse,
    TrackingResponse,
)
from app.services.email_service import EmailService

logger = logging.getLogger("amc.api.email")

router = APIRouter(prefix="/email", tags=["email"])


# ── Helper ───────────────────────────────────────────────────────────────────


def _template_to_response(template) -> EmailTemplateResponse:
    """Convert an ORM EmailTemplate to a response schema."""
    return EmailTemplateResponse(
        id=template.id,
        tenant_id=template.tenant_id,
        workspace_id=template.workspace_id,
        name=template.name,
        subject=template.subject,
        preheader=template.preheader,
        body_html=template.body_html,
        body_text=template.body_text,
        category=template.category,
        variables=template.variables,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _delivery_to_response(msg) -> DeliveryResponse:
    """Convert an ORM EmailMessage to a delivery response schema."""
    return DeliveryResponse(
        id=msg.id,
        tenant_id=msg.tenant_id,
        campaign_id=msg.campaign_id,
        recipient_email=msg.recipient_email,
        recipient_name=msg.recipient_name,
        subject=msg.subject,
        status=msg.status,
        provider=msg.provider,
        provider_message_id=msg.provider_message_id,
        tracking_id=msg.tracking_id,
        opened_at=msg.opened_at,
        open_count=msg.open_count or 0,
        clicked_at=msg.clicked_at,
        click_count=msg.click_count or 0,
        bounced_at=msg.bounced_at,
        bounce_type=msg.bounce_type,
        complained_at=msg.complained_at,
        queued_at=msg.queued_at,
        sent_at=msg.sent_at,
        delivered_at=msg.delivered_at,
        failed_at=msg.failed_at,
        error_message=msg.error_message,
        created_at=msg.created_at,
        updated_at=msg.updated_at,
    )


def _campaign_to_response(campaign) -> CampaignResponse:
    """Convert an ORM EmailCampaign to a response schema."""
    return CampaignResponse(
        id=campaign.id,
        tenant_id=campaign.tenant_id,
        workspace_id=campaign.workspace_id,
        name=campaign.name,
        description=campaign.description,
        status=campaign.status,
        provider=campaign.provider,
        total_recipients=campaign.total_recipients or 0,
        sent_count=campaign.sent_count or 0,
        delivered_count=campaign.delivered_count or 0,
        bounced_count=campaign.bounced_count or 0,
        complained_count=campaign.complained_count or 0,
        opened_count=campaign.opened_count or 0,
        clicked_count=campaign.clicked_count or 0,
        failed_count=campaign.failed_count or 0,
        scheduled_at=campaign.scheduled_at,
        started_at=campaign.started_at,
        completed_at=campaign.completed_at,
        tracking_enabled=campaign.tracking_enabled,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


# ── Send ──────────────────────────────────────────────────────────────────────


@router.post("/send", status_code=201)
async def send_email(
    body: SendRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a single email.

    Supports direct content (``body_html`` / ``body_text``) or template-based
    rendering via ``template_id`` + ``template_variables``.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = UUID(x_workspace_id) if x_workspace_id else None

    service = EmailService(db)

    result = await service.send_email(
        to=body.to if isinstance(body.to, str) else body.to,
        subject=body.subject,
        body_html=body.body_html,
        body_text=body.body_text,
        from_email=body.from_email,
        from_name=body.from_name,
        reply_to=body.reply_to,
        to_name=body.to_name,
        template_id=body.template_id,
        template_variables=body.template_variables,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        tracking_enabled=body.tracking_enabled,
        provider=body.provider,
        metadata=body.metadata,
    )

    return build_single_response(
        SendResponse(
            message="Email sent successfully" if result.success else "Email queued",
            message_id=result.message_id,
            tracking_id=result.tracking_id,
            status=result.status,
        )
    )


@router.post("/send-bulk", status_code=201)
async def send_bulk(
    body: SendBulkRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Send a bulk email campaign to multiple recipients.

    Creates an ``EmailCampaign`` record and queues all messages.
    Supports template rendering with per-recipient variable overrides.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = UUID(x_workspace_id) if x_workspace_id else None

    service = EmailService(db)

    recipients = [
        {
            "email": r.email if isinstance(r.email, str) else r.email,
            "name": r.name,
            "variables": r.variables,
        }
        for r in body.recipients
    ]

    campaign, results = await service.send_bulk(
        campaign_name=body.campaign_name,
        recipients=recipients,
        subject=body.subject,
        body_html=body.body_html,
        body_text=body.body_text,
        from_email=body.from_email,
        from_name=body.from_name,
        reply_to=body.reply_to,
        template_id=body.template_id,
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        tracking_enabled=body.tracking_enabled,
        provider=body.provider,
        scheduled_at=body.scheduled_at,
        max_emails_per_minute=body.max_emails_per_minute,
        metadata=body.metadata,
    )

    success_count = sum(1 for r in results if r.success)
    failed_count = sum(1 for r in results if not r.success)

    return build_single_response(
        SendBulkResponse(
            message=f"Campaign '{campaign.name}' — {success_count} sent, {failed_count} failed",
            campaign_id=campaign.id,
            total_recipients=len(results),
            status=campaign.status,
        )
    )


# ── Templates ────────────────────────────────────────────────────────────────


@router.get("/templates")
async def list_templates(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    category: str | None = Query(None),
) -> dict:
    """List email templates with optional category filter."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = UUID(x_workspace_id) if x_workspace_id else None

    service = EmailService(db)
    skip = (page - 1) * limit

    items, total = await service.list_templates(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
        category=category,
    )

    return build_list_response(
        data=[_template_to_response(t) for t in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/templates/{template_id}")
async def get_template(
    template_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single email template."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = EmailService(db)
    template = await service.get_template(template_id, tenant_id=tenant_id)
    return build_single_response(_template_to_response(template))


@router.post("/templates", status_code=201)
async def create_template(
    body: EmailTemplateCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new email template.

    The template body may contain Jinja2 placeholders (``{{ variable }}``)
    that will be rendered at send time.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = UUID(x_workspace_id) if x_workspace_id else UUID(int=0)

    service = EmailService(db)

    if workspace_id == UUID(int=0):
        # Fall back: try to get default workspace
        from app.models.tenant import UserRole
        from sqlalchemy import select
        stmt = (
            select(UserRole.workspace_id)
            .where(UserRole.user_id == current_user.id)
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.first()
        if row:
            workspace_id = row[0]

    template = await service.create_template(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        name=body.name,
        subject=body.subject,
        body_html=body.body_html,
        body_text=body.body_text,
        preheader=body.preheader,
        category=body.category,
        variables=body.variables,
    )
    return build_single_response(_template_to_response(template))


@router.patch("/templates/{template_id}")
async def update_template(
    template_id: UUID,
    body: EmailTemplateUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update an email template."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = EmailService(db)
    template = await service.update_template(
        template_id,
        tenant_id=tenant_id,
        **body.model_dump(exclude_unset=True),
    )
    return build_single_response(_template_to_response(template))


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete an email template."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = EmailService(db)
    await service.delete_template(template_id, tenant_id=tenant_id)
    return None


# ── Deliveries / History ─────────────────────────────────────────────────────


@router.get("/deliveries")
async def list_deliveries(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    status: str | None = Query(None),
    campaign_id: UUID | None = Query(None),
    recipient_email: str | None = Query(None),
) -> dict:
    """List email delivery history with optional filters.

    Filterable by ``status``, ``campaign_id``, and ``recipient_email``.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = UUID(x_workspace_id) if x_workspace_id else None

    service = EmailService(db)
    skip = (page - 1) * limit

    items, total = await service.list_deliveries(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        campaign_id=campaign_id,
        status=status,
        recipient_email=recipient_email,
        skip=skip,
        limit=limit,
    )

    return build_list_response(
        data=[_delivery_to_response(m) for m in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/deliveries/{message_id}")
async def get_delivery(
    message_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single delivery record by ID."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = EmailService(db)
    message = await service.get_delivery(message_id, tenant_id=tenant_id)
    return build_single_response(_delivery_to_response(message))


# ── Campaigns ────────────────────────────────────────────────────────────────


@router.get("/campaigns")
async def list_campaigns(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    x_workspace_id: str | None = Header(None, alias="X-Workspace-ID"),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List email campaigns with delivery stats."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    workspace_id = UUID(x_workspace_id) if x_workspace_id else None

    service = EmailService(db)
    skip = (page - 1) * limit

    items, total = await service.list_campaigns(
        tenant_id=tenant_id,
        workspace_id=workspace_id,
        skip=skip,
        limit=limit,
    )

    return build_list_response(
        data=[_campaign_to_response(c) for c in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single email campaign with aggregate stats."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = EmailService(db)
    campaign = await service.get_campaign(campaign_id, tenant_id=tenant_id)
    return build_single_response(_campaign_to_response(campaign))


# ── Bounce / Complaint Webhook ────────────────────────────────────────────────


@router.post("/bounce-webhook")
async def bounce_webhook(
    body: BounceWebhookPayload,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Receive bounce, complaint, and delivery notifications.

    Accepts SES SNS notifications and direct webhook payloads.
    The raw payload is processed to update message delivery status.
    """
    service = EmailService(db)

    if body.provider == "ses":
        # Parse SES SNS notification
        result = await service.process_sns_notification(body.raw_payload)
    else:
        # Direct bounce/complaint webhook
        if body.event_type == "bounce":
            await service.process_bounce(
                message_id=body.message_id,
                recipient_email=body.recipient_email,
                bounce_type=body.bounce_type or "permanent",
                bounce_reason=body.bounce_reason,
                raw_payload=body.raw_payload,
            )
        elif body.event_type == "complaint":
            await service.process_complaint(
                message_id=body.message_id,
                recipient_email=body.recipient_email,
                complaint_feedback_type=body.complaint_feedback_type,
                raw_payload=body.raw_payload,
            )
        elif body.event_type == "delivery":
            await service.process_delivery(
                message_id=body.message_id,
                recipient_email=body.recipient_email,
            )
        result = {"processed": True, "event_type": body.event_type}

    return build_single_response(result)


# ── Tracking endpoints ────────────────────────────────────────────────────────


@router.get("/track/open/{tracking_id}")
async def track_open(
    tracking_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> str:
    """Record an email open event via 1x1 tracking pixel.

    Returns a transparent 1x1 GIF. The tracking endpoint does not
    require authentication (it is embedded in emails).
    """
    service = EmailService(db)
    await service.record_open(tracking_id)

    # Return 1x1 transparent GIF
    from base64 import b64decode

    pixel_b64 = (
        "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
    )
    return b64decode(pixel_b64)


@router.get("/track/click/{tracking_id}")
async def track_click(
    tracking_id: str,
    request: Request,
    url: str = Query(..., description="Original target URL"),
    db: AsyncSession = Depends(get_db),
):
    """Record an email click event and redirect to the target URL.

    All links in tracked emails are rewritten to go through this
    endpoint. It records the click and issues a 302 redirect.
    """
    service = EmailService(db)
    await service.record_click(tracking_id, url)

    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=url, status_code=302)
