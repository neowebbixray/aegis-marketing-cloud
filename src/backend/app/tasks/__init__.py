"""Celery async task queue configuration."""
from __future__ import annotations

from celery import Celery

from app.config import settings

celery_app = Celery(
    "aegis",
    broker=settings.rabbitmq_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.email",
        "app.tasks.ai",
        "app.tasks.workflows",
        "app.tasks.reports",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    worker_max_tasks_per_child=200,
    worker_prefetch_multiplier=1,
    result_expires=3600 * 24 * 7,
    task_acks_late=True,
    worker_concurrency=4,
)


@celery_app.task(bind=True, max_retries=3)
def debug_task(self) -> str:
    """Debug task to verify Celery is running."""
    print(f"Request: {self.request!r}")
    return f"Celery worker OK — {settings.app_name}"
