"""Email tasks — send transactional and campaign emails."""
from app.tasks import celery_app


@celery_app.task(bind=True, max_retries=3)
def send_email(self, to: str, subject: str, body_html: str, body_text: str | None = None) -> bool:
    """Send a single email."""
    from app.services.email import send_email as _send

    return _send(to=to, subject=subject, body_html=body_html, body_text=body_text)


@celery_app.task(bind=True, max_retries=3)
def send_campaign_emails(self, campaign_id: str) -> int:
    """Send all emails for a campaign."""
    from app.services.email import send_campaign

    return send_campaign(campaign_id=campaign_id)
