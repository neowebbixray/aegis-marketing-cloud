"""Workflow trigger tasks — bridges n8n with AMC backend."""

from app.tasks import celery_app


@celery_app.task(bind=True, max_retries=3)
def trigger_workflow(self, workflow_id: str, payload: dict) -> dict:
    """Trigger an n8n webhook workflow."""
    from app.services.workflows import trigger

    return trigger(workflow_id=workflow_id, payload=payload)


@celery_app.task(bind=True, max_retries=2)
def process_email_reply(self, message_id: str) -> bool:
    """Process an incoming email reply and link to workflow."""
    from app.services.workflows import process_reply

    return process_reply(message_id=message_id)
