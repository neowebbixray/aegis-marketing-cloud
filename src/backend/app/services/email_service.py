"""Email delivery engine — SMTP and Amazon SES backends with open/click
tracking, template rendering (Jinja2), rate limiting, and bounce handling.

Usage::

    from app.services.email_service import EmailService

    service = EmailService(db_session)
    result = await service.send_email(
        to="user@example.com",
        subject="Hello",
        body_html="<h1>Hi {{ name }}</h1>",
        template_variables={"name": "Alice"},
    )
"""
from __future__ import annotations

import asyncio
import email.utils
import hashlib
import hmac
import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from io import BytesIO
from typing import Any
from urllib.parse import quote, urlparse
from uuid import UUID

from sqlalchemy import select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.email import EmailCampaign, EmailMessage
from app.models.marketing import EmailTemplate

logger = logging.getLogger("amc.services.email")

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

TRACKING_PIXEL = (
    "data:image/gif;base64,"
    "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"
)

# Rate limiting: default max emails per minute per workspace
DEFAULT_RATE_LIMIT = 60  # emails per minute


class EmailDeliveryStatus(str, Enum):
    """Possible delivery statuses for an email message."""

    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    BOUNCED = "bounced"
    COMPLAINED = "complained"
    FAILED = "failed"


class BounceType(str, Enum):
    PERMANENT = "permanent"
    TRANSIENT = "transient"
    UNDETERMINED = "undetermined"


# ─────────────────────────────────────────────────────────────────────────────
# Data types
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class EmailData:
    """The prepared content of an email message ready for sending."""

    to: str
    to_name: str | None
    subject: str
    body_html: str | None = None
    body_text: str | None = None
    from_email: str = ""
    from_name: str | None = None
    reply_to: str | None = None
    tracking_id: str | None = None
    tracking_enabled: bool = True
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class SendResult:
    """Result of sending a single email."""

    success: bool
    message_id: UUID
    provider_message_id: str | None = None
    tracking_id: str | None = None
    status: str = "queued"
    error_message: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Template engine
# ─────────────────────────────────────────────────────────────────────────────


class EmailTemplateEngine:
    """Jinja2-based template rendering for email content."""

    def __init__(self) -> None:
        self._env: Any = None

    @property
    def env(self) -> Any:
        """Lazy-initialised Jinja2 environment."""
        if self._env is None:
            try:
                from jinja2 import Environment, select_autoescape

                self._env = Environment(
                    autoescape=select_autoescape(
                        enabled_extensions=("html",),
                        default_for_string=False,
                    ),
                    enable_async=True,
                )
            except ImportError:
                logger.warning(
                    "Jinja2 not available — template rendering disabled. "
                    "Install with: pip install jinja2"
                )
                self._env = None
        return self._env

    async def render(
        self,
        template_content: str,
        variables: dict[str, Any] | None = None,
    ) -> str:
        """Render a Jinja2 template string with *variables*."""
        if self.env is None:
            # No Jinja2 — return as-is (no substitution)
            return template_content
        tpl = self.env.from_string(template_content)
        return await tpl.render_async(**(variables or {}))

    async def render_template_model(
        self,
        template: EmailTemplate,
        variables: dict[str, Any] | None = None,
    ) -> tuple[str, str | None, str | None]:
        """Render an :class:`EmailTemplate` ORM object.

        Returns ``(subject, body_html, body_text)``.
        """
        vars = variables or {}
        subject = await self.render(template.subject, vars)
        html = (
            await self.render(template.body_html, vars)
            if template.body_html
            else None
        )
        text = (
            await self.render(template.body_text, vars)
            if template.body_text
            else None
        )
        return subject, html, text


_template_engine = EmailTemplateEngine()


# ─────────────────────────────────────────────────────────────────────────────
# Tracking helpers
# ─────────────────────────────────────────────────────────────────────────────


def generate_tracking_id() -> str:
    """Generate a unique tracking ID for open/click tracking."""
    return uuid.uuid4().hex[:32]


def inject_tracking_pixel(
    body_html: str, tracking_url: str, tracking_id: str
) -> str:
    """Inject a 1x1 transparent tracking pixel just before ``</body>``.

    The pixel URL is ``{tracking_url}/open/{tracking_id}``.
    """
    pixel_tag = (
        f'<img src="{tracking_url}/open/{tracking_id}" '
        f'alt="" width="1" height="1" border="0" '
        f'style="display:none;width:1px!important;height:1px!important;" />'
    )
    # Inject before </body>
    if "</body>" in body_html:
        body_html = body_html.replace("</body>", f"{pixel_tag}\n</body>")
    else:
        body_html = f"{body_html}\n{pixel_tag}"
    return body_html


def rewrite_links(
    body_html: str, tracking_url: str, tracking_id: str
) -> str:
    """Rewrite all ``href=`` links to go through the click tracking endpoint.

    Original URL is encoded as a query parameter.
    """
    def _replace_link(match: re.Match) -> str:
        prefix = match.group(1)
        url = match.group(2)
        # Don't rewrite tracking links, mailto:, or anchors
        if url.startswith("#") or url.startswith("mailto:"):
            return match.group(0)
        encoded = quote(url, safe="")
        tracked_url = f"{tracking_url}/click/{tracking_id}?url={encoded}"
        return f'{prefix}"{tracked_url}"'

    # Match href="..." and href='...'
    pattern = re.compile(r'(href\s*=\s*)"([^"]+)"', re.IGNORECASE)
    body_html = pattern.sub(_replace_link, body_html)
    pattern2 = re.compile(r"(href\s*=\s*)'([^']+)'", re.IGNORECASE)
    body_html = pattern2.sub(_replace_link, body_html)
    return body_html


# ─────────────────────────────────────────────────────────────────────────────
# Rate limiter
# ─────────────────────────────────────────────────────────────────────────────


class RateLimiter:
    """Simple in-memory rate limiter for email sending.

    Tracks sent count per workspace per time window.
    This is a placeholder — in production, use Redis or a distributed
    counter.
    """

    def __init__(self) -> None:
        self._counts: dict[str, list[float]] = {}

    def _key(self, workspace_id: UUID) -> str:
        return f"email_rate:{workspace_id}"

    def check(self, workspace_id: UUID, max_per_minute: int = DEFAULT_RATE_LIMIT) -> bool:
        """Check if sending is allowed for *workspace_id*.

        Returns ``True`` if under the limit, ``False`` if rate-limited.
        """
        key = self._key(workspace_id)
        now = datetime.now(timezone.utc).timestamp()
        window = 60.0  # 1 minute

        # Prune entries outside the window
        if key in self._counts:
            self._counts[key] = [
                t for t in self._counts[key] if now - t < window
            ]

        current_count = len(self._counts.get(key, []))
        return current_count < max_per_minute

    def increment(self, workspace_id: UUID) -> None:
        """Record a send for *workspace_id*."""
        key = self._key(workspace_id)
        now = datetime.now(timezone.utc).timestamp()
        if key not in self._counts:
            self._counts[key] = []
        self._counts[key].append(now)

    def remaining(self, workspace_id: UUID, max_per_minute: int = DEFAULT_RATE_LIMIT) -> int:
        """Return remaining email capacity for this minute window."""
        key = self._key(workspace_id)
        now = datetime.now(timezone.utc).timestamp()
        if key in self._counts:
            self._counts[key] = [
                t for t in self._counts[key] if now - t < 60.0
            ]
            used = len(self._counts[key])
        else:
            used = 0
        return max(max_per_minute - used, 0)


_rate_limiter = RateLimiter()


# ─────────────────────────────────────────────────────────────────────────────
# SMTP backend
# ─────────────────────────────────────────────────────────────────────────────


class SMTPSender:
    """Send emails via SMTP using aiosmtplib."""

    def __init__(self) -> None:
        self._client: Any = None

    async def _get_client(self) -> Any:
        """Lazy-initialise the SMTP client."""
        if self._client is None:
            try:
                from aiosmtplib import SMTP

                self._client = SMTP(
                    hostname=settings.smtp_host,
                    port=settings.smtp_port,
                    use_tls=settings.smtp_tls,
                )
            except ImportError:
                raise ImportError(
                    "aiosmtplib is required for SMTP sending. "
                    "Install: pip install aiosmtplib"
                )
        return self._client

    async def send(
        self,
        email_data: EmailData,
    ) -> str | None:
        """Send an email via SMTP.

        Returns the provider message ID if available, or ``None``.
        """
        client = await self._get_client()

        # Build MIME message
        import email.mime.multipart
        import email.mime.text

        msg = email.mime.multipart.MIMEMultipart("alternative")
        msg["From"] = email.utils.formataddr(
            (email_data.from_name or "", email_data.from_email)
        )
        msg["To"] = email.utils.formataddr(
            (email_data.to_name or "", email_data.to)
        )
        msg["Subject"] = email_data.subject
        if email_data.reply_to:
            msg["Reply-To"] = email_data.reply_to
        msg["Message-ID"] = email.utils.make_msgid(domain="aegismc.com")

        # Custom headers
        for key, value in email_data.headers.items():
            msg[key] = value

        # Attach parts
        if email_data.body_text:
            msg.attach(
                email.mime.text.MIMEText(email_data.body_text, "plain")
            )
        if email_data.body_html:
            msg.attach(
                email.mime.text.MIMEText(email_data.body_html, "html")
            )

        # Connect and send
        async with client:
            if settings.smtp_user and settings.smtp_password:
                await client.login(settings.smtp_user, settings.smtp_password)
            response = await client.send_message(msg)
            # response is bytes or string; extract msg id if present
            return str(msg["Message-ID"])

        return None


# ─────────────────────────────────────────────────────────────────────────────
# SES backend
# ─────────────────────────────────────────────────────────────────────────────


class SESBackend:
    """Send emails via Amazon SES using boto3."""

    def __init__(self) -> None:
        self._client: Any = None

    @property
    def client(self) -> Any:
        """Lazy-initialise the boto3 SES client."""
        if self._client is None:
            try:
                import boto3

                session = boto3.Session(
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region or "us-east-1",
                )
                self._client = session.client("sesv2")
            except ImportError:
                raise ImportError(
                    "boto3 is required for SES sending. "
                    "Install: pip install boto3"
                )
        return self._client

    async def send(
        self,
        email_data: EmailData,
    ) -> str | None:
        """Send an email via SES.

        Returns the SES message ID.
        """
        destination = {"ToAddresses": [email_data.to]}

        content: dict[str, Any] = {
            "Subject": {"Data": email_data.subject, "Charset": "UTF-8"},
        }

        if email_data.body_html:
            content["Body"] = {
                "Html": {"Data": email_data.body_html, "Charset": "UTF-8"}
            }
        if email_data.body_text:
            body = content.setdefault("Body", {})
            body["Text"] = {"Data": email_data.body_text, "Charset": "UTF-8"}

        # Build tags for tracking
        tags = []
        if email_data.tracking_id:
            tags.append(
                {"Name": "tracking_id", "Value": email_data.tracking_id}
            )

        # Run in thread executor since boto3 is synchronous
        loop = asyncio.get_running_loop()

        def _send() -> dict[str, Any]:
            kwargs: dict[str, Any] = {
                "FromEmailAddress": email_data.from_email,
                "Destination": destination,
                "Content": {"Simple": content},
            }
            if tags:
                kwargs["EmailTags"] = tags
            if email_data.reply_to:
                kwargs["ReplyToAddresses"] = [email_data.reply_to]

            # Use send_email (SES v2 API)
            return self.client.send_email(**kwargs)

        response = await loop.run_in_executor(None, _send)
        return response.get("MessageId")


# ─────────────────────────────────────────────────────────────────────────────
# EmailService
# ─────────────────────────────────────────────────────────────────────────────


class EmailService:
    """High-level email delivery service.

    Provides single and bulk sending with SMTP/SES backends, template
    rendering, open/click tracking, and bounce processing.

    Typical usage::

        service = EmailService(db)
        result = await service.send_email(
            to="user@example.com",
            subject="Welcome!",
            body_html="<h1>Hello</h1>",
            tenant_id=tenant_id,
            workspace_id=workspace_id,
        )
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._smtp: SMTPSender | None = None
        self._ses: SESBackend | None = None

    @property
    def smtp(self) -> SMTPSender:
        if self._smtp is None:
            self._smtp = SMTPSender()
        return self._smtp

    @property
    def ses(self) -> SESBackend:
        if self._ses is None:
            self._ses = SESBackend()
        return self._ses

    @property
    def tracking_base_url(self) -> str:
        """Base URL for tracking endpoints.

        Configured via ``settings.email_tracking_url`` or falls back to
        the API base URL.
        """
        if hasattr(settings, "email_tracking_url") and settings.email_tracking_url:
            return settings.email_tracking_url.rstrip("/")
        # Fall back to public API URL
        base = getattr(settings, "public_api_url", "http://localhost:8000")
        return f"{base.rstrip('/')}/api/v1/email/track"

    # ── Send single email ─────────────────────────────────────────────────

    async def send_email(
        self,
        to: str,
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        reply_to: str | None = None,
        to_name: str | None = None,
        template_id: UUID | None = None,
        template_variables: dict[str, Any] | None = None,
        tenant_id: UUID | None = None,
        workspace_id: UUID | None = None,
        campaign_id: UUID | None = None,
        tracking_enabled: bool = True,
        provider: str = "smtp",
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        """Send a single email.

        If *template_id* is provided, the subject and body are rendered
        using the stored template with *template_variables*.

        Returns a :class:`SendResult`.
        """
        # ── Resolve content ───────────────────────────────────────────────
        effective_from = from_email or settings.smtp_from
        effective_subject = subject
        effective_html = body_html
        effective_text = body_text

        if template_id:
            template = await self._get_template(template_id, tenant_id)
            rendered = await _template_engine.render_template_model(
                template, template_variables
            )
            effective_subject, effective_html, effective_text = rendered

        # Validate we have at least one body
        if not effective_html and not effective_text:
            raise ValidationException(
                detail="Either body_html or body_text (or a template) is required"
            )

        # ── Tracking ──────────────────────────────────────────────────────
        tracking_id = generate_tracking_id() if tracking_enabled else None
        if tracking_enabled and effective_html:
            effective_html = inject_tracking_pixel(
                effective_html, self.tracking_base_url, tracking_id
            )
            effective_html = rewrite_links(
                effective_html, self.tracking_base_url, tracking_id
            )

        # ── Create message record ─────────────────────────────────────────
        now = datetime.now(timezone.utc)
        message = EmailMessage(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            campaign_id=campaign_id,
            template_id=template_id,
            from_email=effective_from,
            from_name=from_name or None,
            reply_to=reply_to,
            recipient_email=to,
            recipient_name=to_name or None,
            subject=effective_subject,
            body_html=effective_html,
            body_text=effective_text,
            status=EmailDeliveryStatus.QUEUED.value,
            provider=provider,
            tracking_id=tracking_id,
            tracking_enabled=tracking_enabled,
            queued_at=now,
            metadata=metadata or {},
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)

        # ── Rate limiting check ───────────────────────────────────────────
        if workspace_id:
            max_rate = settings.email_rate_limit if hasattr(settings, "email_rate_limit") else DEFAULT_RATE_LIMIT
            if not _rate_limiter.check(workspace_id, max_per_minute=max_rate):
                message.status = EmailDeliveryStatus.QUEUED.value
                await self.db.flush()
                logger.warning(
                    "Rate limited workspace %s — email %s queued",
                    workspace_id, message.id,
                )
                return SendResult(
                    success=False,
                    message_id=message.id,
                    tracking_id=tracking_id,
                    status="queued",
                    error_message="Rate limited — queued for retry",
                )

        # ── Send ──────────────────────────────────────────────────────────
        email_data = EmailData(
            to=to,
            to_name=to_name,
            subject=effective_subject,
            body_html=effective_html,
            body_text=effective_text,
            from_email=effective_from,
            from_name=from_name,
            reply_to=reply_to,
            tracking_id=tracking_id,
            tracking_enabled=tracking_enabled,
        )

        try:
            message.status = EmailDeliveryStatus.SENDING.value
            await self.db.flush()

            if provider == "ses":
                provider_msg_id = await self.ses.send(email_data)
            else:
                provider_msg_id = await self.smtp.send(email_data)

            message.status = EmailDeliveryStatus.SENT.value
            message.sent_at = datetime.now(timezone.utc)
            message.provider_message_id = provider_msg_id

            if workspace_id:
                _rate_limiter.increment(workspace_id)

            await self.db.flush()

            logger.info(
                "Email sent: id=%s to=%s provider=%s msg_id=%s",
                message.id, to, provider, provider_msg_id,
            )

            return SendResult(
                success=True,
                message_id=message.id,
                provider_message_id=provider_msg_id,
                tracking_id=tracking_id,
                status=EmailDeliveryStatus.SENT.value,
            )

        except Exception as exc:
            message.status = EmailDeliveryStatus.FAILED.value
            message.failed_at = datetime.now(timezone.utc)
            message.error_message = str(exc)
            await self.db.flush()

            logger.error(
                "Email send failed: id=%s to=%s error=%s",
                message.id, to, exc,
            )

            return SendResult(
                success=False,
                message_id=message.id,
                tracking_id=tracking_id,
                status=EmailDeliveryStatus.FAILED.value,
                error_message=str(exc),
            )

    # ── Send bulk ────────────────────────────────────────────────────────

    async def send_bulk(
        self,
        campaign_name: str,
        recipients: list[dict[str, Any]],
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        from_email: str | None = None,
        from_name: str | None = None,
        reply_to: str | None = None,
        template_id: UUID | None = None,
        tenant_id: UUID | None = None,
        workspace_id: UUID | None = None,
        tracking_enabled: bool = True,
        provider: str = "smtp",
        scheduled_at: datetime | None = None,
        max_emails_per_minute: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[EmailCampaign, list[SendResult]]:
        """Send emails to multiple recipients (bulk/campaign mode).

        Each recipient dict should have:
            - ``email`` (str, required)
            - ``name`` (str, optional)
            - ``variables`` (dict, optional — per-recipient template vars)

        Creates an :class:`EmailCampaign` record and queues each message.
        Returns ``(campaign, results)``.
        """
        effective_from = from_email or settings.smtp_from
        now = datetime.now(timezone.utc)

        # Create campaign
        campaign = EmailCampaign(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            template_id=template_id,
            name=campaign_name,
            from_email=effective_from,
            from_name=from_name or None,
            reply_to=reply_to or None,
            subject_override=subject,
            status="scheduled" if scheduled_at else "sending",
            provider=provider,
            total_recipients=len(recipients),
            tracking_enabled=tracking_enabled,
            scheduled_at=scheduled_at,
            started_at=None if scheduled_at else now,
            max_emails_per_minute=max_emails_per_minute,
            metadata=metadata or {},
        )
        self.db.add(campaign)
        await self.db.flush()
        await self.db.refresh(campaign)

        results: list[SendResult] = []

        for recipient in recipients:
            recipient_vars = recipient.get("variables") or {}
            effective_subject = subject
            effective_html = body_html
            effective_text = body_text

            if template_id:
                template = await self._get_template(template_id, tenant_id)
                rendered = await _template_engine.render_template_model(
                    template, recipient_vars
                )
                effective_subject, effective_html, effective_text = rendered

            if not effective_html and not effective_text:
                results.append(
                    SendResult(
                        success=False,
                        message_id=uuid.uuid4(),
                        status="failed",
                        error_message="No body content",
                    )
                )
                continue

            # Send individually
            result = await self.send_email(
                to=recipient["email"],
                subject=effective_subject,
                body_html=effective_html,
                body_text=effective_text,
                from_email=effective_from,
                from_name=from_name,
                reply_to=reply_to,
                to_name=recipient.get("name"),
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                campaign_id=campaign.id,
                tracking_enabled=tracking_enabled,
                provider=provider,
                metadata=metadata,
            )
            results.append(result)

        # Update campaign stats
        await self._refresh_campaign_stats(campaign.id)

        return campaign, results

    # ── Campaign management ───────────────────────────────────────────────

    async def _refresh_campaign_stats(self, campaign_id: UUID) -> None:
        """Recalculate aggregate stats for a campaign from its messages."""
        stats = {
            "sent_count": func.count().filter(
                EmailMessage.status.in_([
                    EmailDeliveryStatus.SENT.value,
                    EmailDeliveryStatus.DELIVERED.value,
                    EmailDeliveryStatus.OPENED.value,
                    EmailDeliveryStatus.CLICKED.value,
                ])
            ),
            "delivered_count": func.count().filter(
                EmailMessage.status.in_([
                    EmailDeliveryStatus.DELIVERED.value,
                    EmailDeliveryStatus.OPENED.value,
                    EmailDeliveryStatus.CLICKED.value,
                ])
            ),
            "bounced_count": func.count().filter(
                EmailMessage.status == EmailDeliveryStatus.BOUNCED.value
            ),
            "complained_count": func.count().filter(
                EmailMessage.status == EmailDeliveryStatus.COMPLAINED.value
            ),
            "opened_count": func.count().filter(
                EmailMessage.opened_at.isnot(None)
            ),
            "clicked_count": func.count().filter(
                EmailMessage.clicked_at.isnot(None)
            ),
            "failed_count": func.count().filter(
                EmailMessage.status == EmailDeliveryStatus.FAILED.value
            ),
        }

        # We use a raw query approach for aggregate update
        from sqlalchemy import text as sa_text

        stmt = sa_text(
            """
            UPDATE email_campaigns
            SET
                sent_count = sub.sent_count,
                delivered_count = sub.delivered_count,
                bounced_count = sub.bounced_count,
                complained_count = sub.complained_count,
                opened_count = sub.opened_count,
                clicked_count = sub.clicked_count,
                failed_count = sub.failed_count
            FROM (
                SELECT
                    campaign_id,
                    COUNT(*) FILTER (WHERE status IN ('sent', 'delivered', 'opened', 'clicked')) AS sent_count,
                    COUNT(*) FILTER (WHERE status IN ('delivered', 'opened', 'clicked')) AS delivered_count,
                    COUNT(*) FILTER (WHERE status = 'bounced') AS bounced_count,
                    COUNT(*) FILTER (WHERE status = 'complained') AS complained_count,
                    COUNT(*) FILTER (WHERE opened_at IS NOT NULL) AS opened_count,
                    COUNT(*) FILTER (WHERE clicked_at IS NOT NULL) AS clicked_count,
                    COUNT(*) FILTER (WHERE status = 'failed') AS failed_count
                FROM email_messages
                WHERE campaign_id = :cid
                GROUP BY campaign_id
            ) AS sub
            WHERE email_campaigns.id = :cid
            """
        )
        await self.db.execute(stmt, {"cid": campaign_id})
        await self.db.flush()

    # ── Tracking handlers ─────────────────────────────────────────────────

    async def record_open(self, tracking_id: str) -> bool:
        """Record an open event for a tracked email.

        Returns ``True`` if the message was found and updated.
        """
        stmt = (
            select(EmailMessage)
            .where(EmailMessage.tracking_id == tracking_id)
        )
        result = await self.db.execute(stmt)
        message = result.scalars().first()
        if message is None:
            logger.warning("Open tracking: unknown tracking_id %s", tracking_id)
            return False

        now = datetime.now(timezone.utc)
        message.open_count = (message.open_count or 0) + 1
        if message.opened_at is None:
            message.opened_at = now
            # Update status (opened implies delivered)
            if message.status in (
                EmailDeliveryStatus.SENT.value,
                EmailDeliveryStatus.DELIVERED.value,
            ):
                message.status = EmailDeliveryStatus.OPENED.value
        await self.db.flush()
        return True

    async def record_click(
        self, tracking_id: str, target_url: str
    ) -> bool:
        """Record a click event for a tracked email.

        Returns ``True`` if the message was found and updated.
        """
        stmt = (
            select(EmailMessage)
            .where(EmailMessage.tracking_id == tracking_id)
        )
        result = await self.db.execute(stmt)
        message = result.scalars().first()
        if message is None:
            logger.warning("Click tracking: unknown tracking_id %s", tracking_id)
            return False

        now = datetime.now(timezone.utc)
        message.click_count = (message.click_count or 0) + 1
        if message.clicked_at is None:
            message.clicked_at = now
            if message.status in (
                EmailDeliveryStatus.SENT.value,
                EmailDeliveryStatus.DELIVERED.value,
                EmailDeliveryStatus.OPENED.value,
            ):
                message.status = EmailDeliveryStatus.CLICKED.value
        await self.db.flush()
        return True

    # ── Bounce/complaint processing ───────────────────────────────────────

    async def process_bounce(
        self,
        *,
        message_id: str | None = None,
        tracking_id: str | None = None,
        recipient_email: str | None = None,
        bounce_type: str = "permanent",
        bounce_reason: str | None = None,
        timestamp: datetime | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> bool:
        """Process a bounce notification for an email.

        Looks up the message by **message_id**, **tracking_id**, or
        **recipient_email** (in that order).
        """
        message = await self._find_message(
            provider_message_id=message_id,
            tracking_id=tracking_id,
            recipient_email=recipient_email,
        )
        if message is None:
            logger.warning(
                "Bounce notification: no matching message found "
                "msg_id=%s tracking=%s recipient=%s",
                message_id, tracking_id, recipient_email,
            )
            return False

        now = datetime.now(timezone.utc)
        message.status = EmailDeliveryStatus.BOUNCED.value
        message.bounced_at = now
        message.bounce_type = bounce_type
        message.bounce_reason = bounce_reason or None

        if raw_payload:
            meta = dict(message.metadata or {})
            meta["bounce_raw_payload"] = raw_payload
            message.metadata = meta

        await self.db.flush()
        logger.info(
            "Bounce recorded: msg_id=%s type=%s reason=%s",
            message.id, bounce_type, bounce_reason,
        )
        return True

    async def process_complaint(
        self,
        *,
        message_id: str | None = None,
        tracking_id: str | None = None,
        recipient_email: str | None = None,
        complaint_feedback_type: str | None = None,
        timestamp: datetime | None = None,
        raw_payload: dict[str, Any] | None = None,
    ) -> bool:
        """Process a complaint (abuse report) notification."""
        message = await self._find_message(
            provider_message_id=message_id,
            tracking_id=tracking_id,
            recipient_email=recipient_email,
        )
        if message is None:
            logger.warning(
                "Complaint notification: no matching message found "
                "msg_id=%s tracking=%s recipient=%s",
                message_id, tracking_id, recipient_email,
            )
            return False

        now = datetime.now(timezone.utc)
        message.status = EmailDeliveryStatus.COMPLAINED.value
        message.complained_at = now
        message.complaint_feedback_type = complaint_feedback_type or None

        if raw_payload:
            meta = dict(message.metadata or {})
            meta["complaint_raw_payload"] = raw_payload
            message.metadata = meta

        await self.db.flush()
        logger.info(
            "Complaint recorded: msg_id=%s type=%s",
            message.id, complaint_feedback_type,
        )
        return True

    async def process_delivery(
        self,
        *,
        message_id: str | None = None,
        tracking_id: str | None = None,
        recipient_email: str | None = None,
        timestamp: datetime | None = None,
    ) -> bool:
        """Record a delivery confirmation."""
        message = await self._find_message(
            provider_message_id=message_id,
            tracking_id=tracking_id,
            recipient_email=recipient_email,
        )
        if message is None:
            return False

        now = datetime.now(timezone.utc)
        message.status = EmailDeliveryStatus.DELIVERED.value
        message.delivered_at = now
        await self.db.flush()
        return True

    # ── SES SNS webhook processing ────────────────────────────────────────

    async def process_sns_notification(
        self, raw_payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Process an SES SNS notification (bounce, complaint, delivery).

        Returns a dict with keys ``processed``, ``event_type``, and
        ``message_id``.
        """
        event_type = raw_payload.get("notificationType", "").lower()
        mail = raw_payload.get("mail", {})
        provider_message_id = mail.get("messageId")

        result: dict[str, Any] = {
            "processed": False,
            "event_type": event_type,
            "message_id": provider_message_id,
        }

        if event_type == "bounce":
            bounce = raw_payload.get("bounce", {})
            bounce_type_raw = bounce.get("bounceType", "").lower()
            if bounce_type_raw == "permanent":
                bt = "permanent"
            elif bounce_type_raw == "transient":
                bt = "transient"
            else:
                bt = "undetermined"

            recipients = bounce.get("bouncedRecipients", [])
            for rcpt in recipients:
                await self.process_bounce(
                    message_id=provider_message_id,
                    recipient_email=rcpt.get("emailAddress"),
                    bounce_type=bt,
                    bounce_reason=rcpt.get("diagnosticCode") or bounce.get("diagnosticCode"),
                    raw_payload=raw_payload,
                )
            result["processed"] = True
            result["recipient_count"] = len(recipients)

        elif event_type == "complaint":
            complaint = raw_payload.get("complaint", {})
            recipients = complaint.get("complainedRecipients", [])
            for rcpt in recipients:
                await self.process_complaint(
                    message_id=provider_message_id,
                    recipient_email=rcpt.get("emailAddress"),
                    complaint_feedback_type=complaint.get("complaintFeedbackType"),
                    raw_payload=raw_payload,
                )
            result["processed"] = True
            result["recipient_count"] = len(recipients)

        elif event_type == "delivery":
            delivery = raw_payload.get("delivery", {})
            recipients = delivery.get("recipients", [])
            for rcpt in recipients:
                await self.process_delivery(
                    message_id=provider_message_id,
                    recipient_email=rcpt,
                )
            result["processed"] = True
            result["recipient_count"] = len(recipients)

        else:
            logger.info("Unhandled SNS notification type: %s", event_type)

        return result

    # ── Template operations ───────────────────────────────────────────────

    async def create_template(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        name: str,
        subject: str,
        body_html: str | None = None,
        body_text: str | None = None,
        preheader: str | None = None,
        category: str | None = None,
        variables: list[str] | None = None,
    ) -> EmailTemplate:
        """Create a new email template."""
        template = EmailTemplate(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            name=name,
            subject=subject,
            preheader=preheader or None,
            body_html=body_html or "",
            body_text=body_text or None,
            category=category or None,
            variables=variables or [],
        )
        self.db.add(template)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def list_templates(
        self,
        tenant_id: UUID,
        workspace_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
        category: str | None = None,
    ) -> tuple[list[EmailTemplate], int]:
        """List email templates for a tenant."""
        stmt = (
            select(EmailTemplate)
            .where(EmailTemplate.tenant_id == tenant_id)
            .where(EmailTemplate.deleted_at.is_(None))
        )
        if workspace_id:
            stmt = stmt.where(EmailTemplate.workspace_id == workspace_id)
        if category:
            stmt = stmt.where(EmailTemplate.category == category)

        # Count
        count_stmt = select(func.count()).select_from(EmailTemplate)
        count_stmt = count_stmt.where(EmailTemplate.tenant_id == tenant_id)
        count_stmt = count_stmt.where(EmailTemplate.deleted_at.is_(None))
        if workspace_id:
            count_stmt = count_stmt.where(EmailTemplate.workspace_id == workspace_id)
        if category:
            count_stmt = count_stmt.where(EmailTemplate.category == category)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Data
        stmt = stmt.order_by(EmailTemplate.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_template(
        self, template_id: UUID, tenant_id: UUID | None = None
    ) -> EmailTemplate:
        """Get a single template by ID."""
        return await self._get_template(template_id, tenant_id)

    async def update_template(
        self,
        template_id: UUID,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> EmailTemplate:
        """Update an email template."""
        template = await self._get_template(template_id, tenant_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(template, key, value)
        await self.db.flush()
        await self.db.refresh(template)
        return template

    async def delete_template(
        self, template_id: UUID, tenant_id: UUID
    ) -> None:
        """Soft-delete an email template."""
        template = await self._get_template(template_id, tenant_id)
        template.soft_delete()
        await self.db.flush()

    # ── Delivery history ──────────────────────────────────────────────────

    async def list_deliveries(
        self,
        tenant_id: UUID,
        workspace_id: UUID | None = None,
        campaign_id: UUID | None = None,
        status: str | None = None,
        recipient_email: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[EmailMessage], int]:
        """List delivery records with optional filters."""
        stmt = select(EmailMessage).where(EmailMessage.tenant_id == tenant_id)
        count_stmt = (
            select(func.count())
            .select_from(EmailMessage)
            .where(EmailMessage.tenant_id == tenant_id)
        )

        if workspace_id:
            stmt = stmt.where(EmailMessage.workspace_id == workspace_id)
            count_stmt = count_stmt.where(EmailMessage.workspace_id == workspace_id)
        if campaign_id:
            stmt = stmt.where(EmailMessage.campaign_id == campaign_id)
            count_stmt = count_stmt.where(EmailMessage.campaign_id == campaign_id)
        if status:
            stmt = stmt.where(EmailMessage.status == status)
            count_stmt = count_stmt.where(EmailMessage.status == status)
        if recipient_email:
            stmt = stmt.where(EmailMessage.recipient_email == recipient_email)
            count_stmt = count_stmt.where(EmailMessage.recipient_email == recipient_email)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(EmailMessage.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_delivery(
        self, message_id: UUID, tenant_id: UUID
    ) -> EmailMessage:
        """Get a single delivery record."""
        stmt = (
            select(EmailMessage)
            .where(EmailMessage.id == message_id)
            .where(EmailMessage.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        message = result.scalars().first()
        if message is None:
            raise NotFoundException(detail="Email delivery record not found")
        return message

    async def list_campaigns(
        self,
        tenant_id: UUID,
        workspace_id: UUID | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[EmailCampaign], int]:
        """List email campaigns."""
        stmt = (
            select(EmailCampaign)
            .where(EmailCampaign.tenant_id == tenant_id)
            .where(EmailCampaign.deleted_at.is_(None))
        )
        count_stmt = (
            select(func.count())
            .select_from(EmailCampaign)
            .where(EmailCampaign.tenant_id == tenant_id)
            .where(EmailCampaign.deleted_at.is_(None))
        )
        if workspace_id:
            stmt = stmt.where(EmailCampaign.workspace_id == workspace_id)
            count_stmt = count_stmt.where(EmailCampaign.workspace_id == workspace_id)

        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.order_by(EmailCampaign.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def get_campaign(
        self, campaign_id: UUID, tenant_id: UUID
    ) -> EmailCampaign:
        """Get a single campaign."""
        stmt = (
            select(EmailCampaign)
            .where(EmailCampaign.id == campaign_id)
            .where(EmailCampaign.tenant_id == tenant_id)
        )
        result = await self.db.execute(stmt)
        campaign = result.scalars().first()
        if campaign is None:
            raise NotFoundException(detail="Email campaign not found")
        return campaign

    # ── Internal helpers ──────────────────────────────────────────────────

    async def _get_template(
        self, template_id: UUID, tenant_id: UUID | None = None
    ) -> EmailTemplate:
        """Fetch an email template by ID, optionally scoped to tenant."""
        stmt = select(EmailTemplate).where(EmailTemplate.id == template_id)
        if tenant_id:
            stmt = stmt.where(EmailTemplate.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        template = result.scalars().first()
        if template is None:
            raise NotFoundException(detail="Email template not found")
        return template

    async def _find_message(
        self,
        provider_message_id: str | None = None,
        tracking_id: str | None = None,
        recipient_email: str | None = None,
    ) -> EmailMessage | None:
        """Find an email message by various identifiers.

        Tries **provider_message_id** first, then **tracking_id**, then
        **recipient_email** (most recent).
        """
        if provider_message_id:
            stmt = (
                select(EmailMessage)
                .where(
                    EmailMessage.provider_message_id == provider_message_id
                )
                .order_by(EmailMessage.created_at.desc())
                .limit(1)
            )
            result = await self.db.execute(stmt)
            msg = result.scalars().first()
            if msg:
                return msg

        if tracking_id:
            stmt = (
                select(EmailMessage)
                .where(EmailMessage.tracking_id == tracking_id)
                .limit(1)
            )
            result = await self.db.execute(stmt)
            msg = result.scalars().first()
            if msg:
                return msg

        if recipient_email:
            stmt = (
                select(EmailMessage)
                .where(EmailMessage.recipient_email == recipient_email)
                .order_by(EmailMessage.created_at.desc())
                .limit(1)
            )
            result = await self.db.execute(stmt)
            msg = result.scalars().first()
            if msg:
                return msg

        return None
