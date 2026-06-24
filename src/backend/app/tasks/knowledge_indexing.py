"""Celery tasks for async knowledge document indexing.

These tasks are optional — if Celery is not running, callers can invoke
``KnowledgeService.index_document`` directly.
"""

from __future__ import annotations

import logging
from uuid import UUID

logger = logging.getLogger("amc.tasks.knowledge_indexing")

# Attempt to import Celery; gracefully degrade if not available.
try:
    from app.tasks import celery_app

    CELERY_AVAILABLE = True
except (ImportError, Exception):
    celery_app = None  # type: ignore[assignment]
    CELERY_AVAILABLE = False
    logger.info("Celery not available — knowledge indexing tasks will run synchronously")


def _do_index(tenant_id: str, document_id: str) -> dict:
    """Core indexing logic shared by sync and async paths."""
    import asyncio

    from app.database import async_session_factory
    from app.services.knowledge_service import KnowledgeService

    async def _run() -> dict:
        async with async_session_factory() as db:
            service = KnowledgeService(db)
            return await service.index_document(
                tenant_id=UUID(tenant_id),
                document_id=UUID(document_id),
            )

    return asyncio.run(_run())


if CELERY_AVAILABLE and celery_app is not None:

    @celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
    def index_document_task(
        self,
        tenant_id: str,
        document_id: str,
    ) -> dict:
        """Index a single document in Qdrant (async via Celery)."""
        try:
            result = _do_index(tenant_id, document_id)
            logger.info(
                "Celery task indexed document %s for tenant %s: %s",
                document_id,
                tenant_id,
                result,
            )
            return result
        except Exception as exc:
            logger.error(
                "Celery task failed to index document %s: %s",
                document_id,
                exc,
            )
            raise self.retry(exc=exc) from exc

    @celery_app.task(bind=True, max_retries=2, default_retry_delay=60)
    def bulk_index_task(
        self,
        tenant_id: str,
        document_ids: list[str],
    ) -> list[dict]:
        """Index multiple documents in batch."""
        results = []
        for doc_id in document_ids:
            try:
                result = _do_index(tenant_id, doc_id)
                results.append(result)
            except Exception as exc:
                logger.error(
                    "Bulk task failed on document %s: %s",
                    doc_id,
                    exc,
                )
                results.append(
                    {
                        "document_id": doc_id,
                        "chunks_indexed": 0,
                        "is_indexed": False,
                        "error": str(exc),
                    },
                )
        return results

else:
    # Fallback: synchronous stubs for when Celery is not configured.
    def index_document_task(
        tenant_id: str,
        document_id: str,
    ) -> dict:
        """Index a document synchronously (Celery not available)."""
        logger.warning("Celery unavailable — running index synchronously")
        return _do_index(tenant_id, document_id)

    def bulk_index_task(
        tenant_id: str,
        document_ids: list[str],
    ) -> list[dict]:
        """Bulk index synchronously (Celery not available)."""
        logger.warning("Celery unavailable — running bulk index synchronously")
        results = []
        for doc_id in document_ids:
            try:
                results.append(_do_index(tenant_id, doc_id))
            except Exception as exc:
                results.append(
                    {
                        "document_id": doc_id,
                        "chunks_indexed": 0,
                        "is_indexed": False,
                        "error": str(exc),
                    },
                )
        return results
