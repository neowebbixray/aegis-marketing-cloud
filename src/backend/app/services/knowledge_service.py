"""
Knowledge Base service: Qdrant vector store management, document indexing,
semantic search, and embedding generation.

Uses a ``QdrantManager`` singleton for client lifecycle and a ``KnowledgeService``
class for all knowledge-base operations.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import select, func, update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.ai import KnowledgeDocument
from app.services.base import BaseService

logger = logging.getLogger("amc.services.knowledge")

# ─────────────────────────────────────────────────────────────────────────────
# QdrantManager (singleton)
# ─────────────────────────────────────────────────────────────────────────────


class QdrantManager:
    """Singleton managing the Qdrant client and collection lifecycle.

    Lazily initialises the client on first access.  Collections are named
    ``knowledge_{tenant_id}``.
    """

    _instance: QdrantManager | None = None
    _client: Any = None  # qdrant_client.QdrantClient

    def __new__(cls) -> QdrantManager:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── Client ────────────────────────────────────────────────────────────

    @property
    def client(self) -> Any:
        """Lazy-initialised Qdrant client."""
        if self._client is None:
            from qdrant_client import QdrantClient as _QdrantClient

            self._client = _QdrantClient(
                host=settings.qdrant_host,
                port=settings.qdrant_port,
                api_key=settings.qdrant_api_key,
                prefer_grpc=settings.qdrant_prefer_grpc,
                https=settings.qdrant_https,
            )
            logger.info(
                "QdrantClient initialised — %s:%s",
                settings.qdrant_host,
                settings.qdrant_port,
            )
        return self._client

    def _collection_name(self, tenant_id: UUID) -> str:
        return f"knowledge_{tenant_id}"

    # ── Collection management ─────────────────────────────────────────────

    async def create_collection(
        self,
        tenant_id: UUID,
        vector_size: int | None = None,
        distance: str = "Cosine",
    ) -> bool:
        """Create a Qdrant collection for *tenant_id* if it does not exist.

        Returns ``True`` if the collection was created, ``False`` if it
        already existed.
        """
        name = self._collection_name(tenant_id)
        exists = await self.collection_exists(tenant_id)
        if exists:
            return False

        from qdrant_client.http.models import Distance, VectorParams

        dim = vector_size or settings.embedding_dimension
        dist = Distance.COSINE if distance.upper() == "COSINE" else Distance.DOT

        self.client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=dist),
        )
        logger.info("Created Qdrant collection '%s' (dim=%s)", name, dim)
        return True

    async def collection_exists(self, tenant_id: UUID) -> bool:
        """Return ``True`` if a Qdrant collection exists for *tenant_id*."""
        name = self._collection_name(tenant_id)
        collections = self.client.get_collections()
        return any(c.name == name for c in collections.collections)

    async def delete_collection(self, tenant_id: UUID) -> bool:
        """Delete the Qdrant collection for *tenant_id*.

        Returns ``True`` if deleted, ``False`` if it did not exist.
        """
        name = self._collection_name(tenant_id)
        if not await self.collection_exists(tenant_id):
            return False
        self.client.delete_collection(collection_name=name)
        logger.info("Deleted Qdrant collection '%s'", name)
        return True

    async def get_collection_info(self, tenant_id: UUID) -> dict[str, Any]:
        """Return collection info (points count, vector config, etc.)."""
        name = self._collection_name(tenant_id)
        if not await self.collection_exists(tenant_id):
            return {"exists": False}
        info = self.client.get_collection(collection_name=name)
        return {
            "exists": True,
            "points_count": info.points_count,
            "vectors_count": info.vectors_count,
            "config": info.config.model_dump() if hasattr(info.config, "model_dump") else str(info.config),
        }

    # ── Point operations ──────────────────────────────────────────────────

    async def upsert_points(
        self,
        tenant_id: UUID,
        points: list[dict[str, Any]],
    ) -> int:
        """Insert or replace a batch of points.

        Each *point* dict should contain:
            ``id`` (str | UUID), ``vector`` (list[float]),
            ``payload`` (dict).

        Returns the number of points upserted.
        """
        from qdrant_client.http.models import PointStruct

        name = self._collection_name(tenant_id)
        qdrant_points = [
            PointStruct(id=str(p["id"]), vector=p["vector"], payload=p.get("payload", {}))
            for p in points
        ]
        self.client.upsert(collection_name=name, points=qdrant_points)
        logger.debug("Upserted %d points into '%s'", len(points), name)
        return len(points)

    async def delete_points(
        self,
        tenant_id: UUID,
        point_ids: list[str],
    ) -> int:
        """Delete points by their IDs.

        Returns the number of points deleted.
        """
        from qdrant_client.http.models import Filter, FilterSelector, HasIdCondition

        name = self._collection_name(tenant_id)
        self.client.delete(
            collection_name=name,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[HasIdCondition(has_id=point_ids)],
                )
            ),
        )
        logger.debug("Deleted %d points from '%s'", len(point_ids), name)
        return len(point_ids)

    async def delete_points_by_filter(
        self,
        tenant_id: UUID,
        must_filters: list[dict[str, Any]] | None = None,
    ) -> int:
        """Delete points matching a filter.

        Each filter dict should have ``key``, ``match`` (value), or
        ``range`` etc.  See Qdrant filter syntax.
        """
        from qdrant_client.http.models import FieldCondition, Filter, MatchValue

        name = self._collection_name(tenant_id)
        conditions = []
        if must_filters:
            for f in must_filters:
                conditions.append(
                    FieldCondition(
                        key=f["key"],
                        match=MatchValue(value=f["value"]),
                    )
                )
        self.client.delete(
            collection_name=name,
            points_selector=Filter(
                must=conditions,
            ),
        )
        return 0  # Qdrant does not return count for filter deletes

    async def search_points(
        self,
        tenant_id: UUID,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search the collection for nearest neighbours.

        Returns a list of result dicts with keys:
            ``document_id``, ``content``, ``score``, ``chunk_index``,
            ``title``, ``doc_type``, ``source``, ``category``,
            ``tags``, ``metadata``.
        """
        from qdrant_client.http.models import Filter as QdrantFilter
        from qdrant_client.http.models import FieldCondition, MatchValue

        name = self._collection_name(tenant_id)

        # Build optional filters
        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                if value is not None:
                    conditions.append(
                        FieldCondition(key=key, match=MatchValue(value=value))
                    )
            if conditions:
                qdrant_filter = QdrantFilter(must=conditions)

        hits = self.client.search(
            collection_name=name,
            query_vector=query_vector,
            limit=top_k,
            query_filter=qdrant_filter,
            with_payload=True,
        )

        results = []
        for hit in hits:
            payload = hit.payload or {}
            results.append(
                {
                    "document_id": UUID(payload.get("document_id", "")),
                    "title": payload.get("title", ""),
                    "content": payload.get("chunk_text", ""),
                    "score": hit.score,
                    "chunk_index": payload.get("chunk_index"),
                    "doc_type": payload.get("doc_type"),
                    "source": payload.get("source"),
                    "category": payload.get("category"),
                    "tags": payload.get("tags"),
                    "metadata": payload.get("metadata"),
                }
            )
        return results

    async def count_points(self, tenant_id: UUID) -> int:
        """Return the total number of points in the collection."""
        name = self._collection_name(tenant_id)
        if not await self.collection_exists(tenant_id):
            return 0
        info = self.client.get_collection(collection_name=name)
        return info.points_count or 0

    async def scroll_points(
        self,
        tenant_id: UUID,
        filter_key: str | None = None,
        filter_value: Any = None,
    ) -> list[dict[str, Any]]:
        """Scroll / fetch all points matching an optional filter."""
        from qdrant_client.http.models import FieldCondition, Filter as QdrantFilter, MatchValue

        name = self._collection_name(tenant_id)
        qdrant_filter = None
        if filter_key is not None and filter_value is not None:
            qdrant_filter = QdrantFilter(
                must=[FieldCondition(key=filter_key, match=MatchValue(value=filter_value))]
            )

        points = self.client.scroll(
            collection_name=name,
            limit=10000,
            with_payload=True,
            with_vectors=False,
            scroll_filter=qdrant_filter,
        )[0]

        return [
            {
                "id": str(p.id),
                "payload": p.payload,
            }
            for p in points
        ]


# ─────────────────────────────────────────────────────────────────────────────
# Embedding helpers
# ─────────────────────────────────────────────────────────────────────────────


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split *text* into overlapping chunks of *chunk_size* characters.

    Overlap between consecutive chunks is *overlap* characters.
    Returns a list of chunk strings.
    """
    if not text:
        return []
    if chunk_size <= 0:
        return [text]

    chunks: list[str] = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        chunks.append(text[start:end])
        if end == text_len:
            break
        start += max(chunk_size - overlap, 1)

    return chunks


async def generate_embedding(text: str) -> list[float]:
    """Generate a vector embedding for *text*.

    If ``settings.embedding_endpoint`` is configured, calls that HTTP API.
    Otherwise falls back to ``sentence-transformers`` (installed separately
    via the ``embeddings`` extra).  As a last resort, returns a deterministic
    pseudo-random vector for development/testing.
    """
    if settings.embedding_endpoint:
        return await _embedding_via_http(text)

    try:
        return await _embedding_via_sentence_transformers(text)
    except ImportError:
        logger.warning(
            "sentence-transformers not available — using fallback mock embedding. "
            "Install with: pip install aegis-marketing-cloud[embeddings]"
        )
        return _mock_embedding(text)


async def _embedding_via_http(text: str) -> list[float]:
    """Call a remote embedding API (OpenAI-compatible format)."""
    import httpx

    headers = {"Content-Type": "application/json"}
    if settings.embedding_api_key:
        headers["Authorization"] = f"Bearer {settings.embedding_api_key}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            settings.embedding_endpoint,  # type: ignore[arg-type]
            json={"input": text, "model": settings.embedding_model},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        # OpenAI format: {"data": [{"embedding": [...], "index": 0}], "model": "..."}
        return data["data"][0]["embedding"]


async def _embedding_via_sentence_transformers(text: str) -> list[float]:
    """Generate embedding using the ``sentence-transformers`` library.

    Runs the model in a thread executor to avoid blocking the async loop.
    """
    import asyncio
    from functools import partial

    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

    model = SentenceTransformer(settings.embedding_model)
    loop = asyncio.get_running_loop()
    embedding = await loop.run_in_executor(
        None,
        partial(model.encode, text),
    )
    return embedding.tolist()


def _mock_embedding(text: str) -> list[float]:
    """Deterministic pseudo-random embedding for development use only."""
    import hashlib
    import struct

    dim = settings.embedding_dimension
    digest = hashlib.sha256(text.encode()).digest()
    rng_seed = struct.unpack("<I", digest[:4])[0]

    import numpy as np

    rng = np.random.default_rng(rng_seed)
    vec = rng.normal(0, 0.1, dim).astype(np.float32)
    # Normalise to unit length
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


# ─────────────────────────────────────────────────────────────────────────────
# KnowledgeService
# ─────────────────────────────────────────────────────────────────────────────


class KnowledgeService(BaseService):
    """Knowledge document service backed by PostgreSQL + Qdrant vector search.

    Inherits ``get``, ``list``, ``create``, ``update``, ``soft_delete`` from
    ``BaseService`` for the ``KnowledgeDocument`` model.
    """

    model = KnowledgeDocument

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self.qdrant = QdrantManager()

    # ── Document indexing ─────────────────────────────────────────────────

    async def create_collection(self, tenant_id: UUID) -> bool:
        """Ensure a Qdrant collection exists for *tenant_id*.

        Returns ``True`` if created, ``False`` if it already existed.
        """
        return await self.qdrant.create_collection(tenant_id)

    async def index_document(
        self,
        tenant_id: UUID,
        document_id: UUID,
    ) -> dict[str, Any]:
        """Chunk *document_id*, generate embeddings, and upsert into Qdrant.

        Updates the document's ``is_indexed``, ``embedding_id``, and
        ``chunk_count`` columns on success.

        Raises ``NotFoundException`` if the document does not exist.
        """
        doc = await self.get(document_id, tenant_id=tenant_id)

        # Ensure collection exists
        await self.create_collection(tenant_id)

        # Chunk content
        chunks = chunk_text(
            doc.content,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )

        if not chunks:
            raise ValidationException(detail="Document content is empty — nothing to index")

        # Generate embeddings
        points = []
        for idx, chunk in enumerate(chunks):
            vector = await generate_embedding(chunk)
            point_id = uuid.uuid5(
                uuid.NAMESPACE_DNS,
                f"{document_id}:{idx}",
            )
            points.append(
                {
                    "id": str(point_id),
                    "vector": vector,
                    "payload": {
                        "document_id": str(document_id),
                        "tenant_id": str(tenant_id),
                        "chunk_index": idx,
                        "chunk_text": chunk,
                        "title": doc.title,
                        "doc_type": doc.doc_type,
                        "source": doc.source or "",
                        "category": doc.category or "",
                        "tags": doc.tags or [],
                        "metadata": doc.metadata or {},
                    },
                }
            )

        # Upsert to Qdrant
        await self.qdrant.upsert_points(tenant_id, points)

        # Update the DB record
        doc.is_indexed = True
        doc.embedding_id = f"qdrant:{tenant_id}:{document_id}"
        doc.chunk_count = len(chunks)
        await self.db.flush()
        await self.db.refresh(doc)

        logger.info(
            "Indexed document %s — %d chunks for tenant %s",
            document_id,
            len(chunks),
            tenant_id,
        )
        return {
            "document_id": str(document_id),
            "chunks_indexed": len(chunks),
            "is_indexed": True,
        }

    async def index_documents_bulk(
        self,
        tenant_id: UUID,
        document_ids: list[UUID],
    ) -> list[dict[str, Any]]:
        """Batch-index multiple documents.

        Returns a list of result dicts (one per document).
        """
        results = []
        for doc_id in document_ids:
            try:
                result = await self.index_document(tenant_id, doc_id)
                results.append(result)
            except Exception as exc:
                logger.error("Failed to index document %s: %s", doc_id, exc)
                results.append(
                    {
                        "document_id": str(doc_id),
                        "chunks_indexed": 0,
                        "is_indexed": False,
                        "error": str(exc),
                    }
                )
        return results

    # ── Search ────────────────────────────────────────────────────────────

    async def search(
        self,
        tenant_id: UUID,
        query: str,
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Semantic search across all indexed document chunks.

        Generates an embedding for *query*, searches the tenant's Qdrant
        collection, and returns ranked results.

        Each result dict has keys:
            ``document_id``, ``title``, ``content``, ``score``,
            ``chunk_index``, ``doc_type``, ``source``, ``category``,
            ``tags``, ``metadata``.
        """
        if not await self.qdrant.collection_exists(tenant_id):
            return []

        query_vector = await generate_embedding(query)
        return await self.qdrant.search_points(
            tenant_id,
            query_vector,
            top_k=top_k,
            filters=filters,
        )

    async def search_by_vector(
        self,
        tenant_id: UUID,
        embedding: list[float],
        top_k: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Search using a pre-computed embedding vector.

        Useful when the caller already has an embedding (e.g. from a cached
        query or a different model).
        """
        if not await self.qdrant.collection_exists(tenant_id):
            return []
        return await self.qdrant.search_points(
            tenant_id,
            embedding,
            top_k=top_k,
            filters=filters,
        )

    async def semantic_search_cross_tenant(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Cross-tenant semantic search — intended for admin features only.

        Searches *all* Qdrant collections (names matching ``knowledge_*``)
        and merges results.  Use with extreme care in a multi-tenant
        environment.
        """
        from qdrant_client.http.models import Filter as QdrantFilter

        query_vector = await generate_embedding(query)
        all_collections = self.qdrant.client.get_collections()

        results: list[dict[str, Any]] = []
        for col in all_collections.collections:
            if not col.name.startswith("knowledge_"):
                continue
            hits = self.qdrant.client.search(
                collection_name=col.name,
                query_vector=query_vector,
                limit=top_k,
                query_filter=None,
                with_payload=True,
            )
            for hit in hits:
                payload = hit.payload or {}
                results.append(
                    {
                        "tenant_id": col.name.replace("knowledge_", ""),
                        "document_id": UUID(payload.get("document_id", "")),
                        "title": payload.get("title", ""),
                        "content": payload.get("chunk_text", ""),
                        "score": hit.score,
                    }
                )

        # Sort by score descending and trim
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    # ── Document lifecycle ────────────────────────────────────────────────

    async def delete_document(
        self,
        tenant_id: UUID,
        document_id: UUID,
    ) -> None:
        """Delete a document from both the DB and Qdrant.

        Removes all associated chunks from Qdrant before soft-deleting
        the DB record.
        """
        # Remove from Qdrant — scroll for all points with this document_id
        await self._remove_qdrant_points(tenant_id, document_id)

        # Soft-delete from DB
        await self.soft_delete(document_id, tenant_id=tenant_id)

        logger.info("Deleted document %s for tenant %s", document_id, tenant_id)

    async def update_document(
        self,
        tenant_id: UUID,
        document_id: UUID,
        **updates: Any,
    ) -> dict[str, Any]:
        """Update a document's metadata, re-indexing if content changes.

        If ``content`` is included in *updates*, the document is fully
        re-indexed (old Qdrant points removed, new ones inserted).
        Otherwise only the DB record is updated.
        """
        content_changed = "content" in updates

        # Update DB
        obj = await self.update(document_id, tenant_id=tenant_id, **updates)

        if content_changed:
            # Re-index
            await self._remove_qdrant_points(tenant_id, document_id)
            result = await self.index_document(tenant_id, document_id)
            return {
                "document_id": str(document_id),
                "chunks_indexed": result["chunks_indexed"],
                "is_indexed": True,
            }

        return {
            "document_id": str(document_id),
            "is_indexed": obj.is_indexed,
        }

    async def _remove_qdrant_points(
        self,
        tenant_id: UUID,
        document_id: UUID,
    ) -> None:
        """Remove all Qdrant points belonging to *document_id*."""
        if not await self.qdrant.collection_exists(tenant_id):
            return
        points = await self.qdrant.scroll_points(
            tenant_id,
            filter_key="document_id",
            filter_value=str(document_id),
        )
        if points:
            point_ids = [p["id"] for p in points]
            await self.qdrant.delete_points(tenant_id, point_ids)

    # ── Stats ─────────────────────────────────────────────────────────────

    async def get_collection_stats(
        self,
        tenant_id: UUID,
    ) -> dict[str, Any]:
        """Return collection statistics for *tenant_id*.

        Returns a dict with keys:
            ``document_count``, ``chunk_count``, ``avg_chunk_size``,
            ``collection_exists``.
        """
        exists = await self.qdrant.collection_exists(tenant_id)

        # Count indexed documents from DB
        count_stmt = select(func.count()).select_from(KnowledgeDocument).where(
            KnowledgeDocument.tenant_id == tenant_id,
            KnowledgeDocument.is_indexed.is_(True),
        )
        result = await self.db.execute(count_stmt)
        doc_count = result.scalar() or 0

        chunk_count = 0
        avg_chunk_size = 0

        if exists:
            chunk_count = await self.qdrant.count_points(tenant_id)

            # Compute average chunk content length from a sample
            all_points = await self.qdrant.scroll_points(tenant_id)
            if all_points:
                total_len = sum(
                    len(p["payload"].get("chunk_text", ""))
                    for p in all_points
                    if p.get("payload")
                )
                avg_chunk_size = total_len // len(all_points) if all_points else 0

        return {
            "document_count": doc_count,
            "chunk_count": chunk_count,
            "avg_chunk_size": avg_chunk_size,
            "collection_exists": exists,
        }

    async def reindex_all_unindexed(
        self,
        tenant_id: UUID,
    ) -> list[dict[str, Any]]:
        """Re-index all documents that have ``is_indexed=False``.

        Returns a list of result dicts (one per document).
        """
        stmt = (
            select(KnowledgeDocument)
            .where(
                KnowledgeDocument.tenant_id == tenant_id,
                KnowledgeDocument.is_indexed.is_(False),
            )
        )
        result = await self.db.execute(stmt)
        docs = list(result.scalars().all())

        if not docs:
            return []

        doc_ids = [doc.id for doc in docs]
        return await self.index_documents_bulk(tenant_id, doc_ids)
