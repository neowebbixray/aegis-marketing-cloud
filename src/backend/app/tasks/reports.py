"""Report generation tasks — generate and deliver scheduled reports."""

from app.tasks import celery_app


@celery_app.task(bind=True, max_retries=2)
def generate_report(self, report_id: str, format: str = "pdf") -> str:
    """Generate a scheduled report."""
    from app.services.reports import generate

    return generate(report_id=report_id, format=format)


@celery_app.task(bind=True, max_retries=2)
def deliver_scheduled_reports(self) -> int:
    """Deliver all due scheduled reports."""
    from app.services.reports import deliver_scheduled

    return deliver_scheduled()
