"""
Knowledge Base router: document management with Qdrant vector indexing
and semantic search.

All list responses use the ``{data, meta, links}`` envelope.
All single-resource responses use ``{data: {...}}``.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.ai import KnowledgeDocument
from app.models.auth import User
from app.schemas.base import build_list_response, build_single_response
from app.schemas.knowledge import (
    CollectionStatsResponse,
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    DocumentUploadResponse,
    ReindexResponse,
    SearchQuery,
    SearchResponse,
    SearchResult,
)
from app.services.knowledge_service import KnowledgeService

logger = logging.getLogger("amc.api.knowledge")

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


# ── Helper ───────────────────────────────────────────────────────────────────


def _doc_to_response(doc: KnowledgeDocument) -> DocumentResponse:
    """Convert an ORM :class:`KnowledgeDocument` to a response model."""
    return DocumentResponse(
        id=doc.id,
        tenant_id=doc.tenant_id,
        title=doc.title,
        content=doc.content,
        doc_type=doc.doc_type,
        source=doc.source,
        category=doc.category,
        tags=doc.tags or [],
        metadata=doc.metadata or {},
        embedding_id=doc.embedding_id,
        chunk_count=doc.chunk_count,
        is_indexed=doc.is_indexed,
        version=doc.version,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


# ── Documents ────────────────────────────────────────────────────────────────


@router.post("/documents", status_code=201)
async def create_document(
    body: DocumentCreate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create a new knowledge document.

    The document is stored in PostgreSQL only.  Use
    ``POST /knowledge/documents/{id}/index`` to trigger Qdrant indexing.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = KnowledgeService(db)

    doc = await service.create(
        tenant_id=tenant_id,
        title=body.title,
        content=body.content,
        doc_type=body.doc_type,
        source=body.source,
        category=body.category,
        tags=body.tags or [],
        metadata=body.metadata or {},
    )
    return build_single_response(_doc_to_response(doc))


@router.post("/documents/upload", status_code=201)
async def upload_document(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
) -> dict:
    """Upload a text file and auto-index it.

    The file content is read as UTF-8 text, stored as a knowledge document,
    and immediately indexed into Qdrant.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)

    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content = content_bytes.decode("latin-1")

    title = file.filename or "Untitled upload"

    service = KnowledgeService(db)
    doc = await service.create(
        tenant_id=tenant_id,
        title=title,
        content=content,
        doc_type="upload",
        source=file.filename,
    )

    # Auto-index
    result = await service.index_document(tenant_id, doc.id)

    return build_single_response(
        DocumentUploadResponse(
            document=_doc_to_response(doc),
            chunks_indexed=result["chunks_indexed"],
            message="Document uploaded and indexed successfully",
        )
    )


@router.get("/documents")
async def list_documents(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    category: str | None = Query(None),
    doc_type: str | None = Query(None),
    tags: str | None = Query(None, description="Comma-separated tags"),
) -> dict:
    """List knowledge documents with optional filters.

    Supports filtering by ``category``, ``doc_type``, and ``tags``.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = KnowledgeService(db)
    skip = (page - 1) * limit

    from sqlalchemy import or_
    from sqlalchemy.sql import ColumnElement

    filters: list[ColumnElement] = []
    if category:
        filters.append(KnowledgeDocument.category == category)
    if doc_type:
        filters.append(KnowledgeDocument.doc_type == doc_type)
    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            # Match documents whose tags array contains any of the given tags
            from sqlalchemy.dialects.postgresql import ARRAY
            filters.append(
                KnowledgeDocument.tags.overlap(tag_list)  # type: ignore[attr-defined]
            )

    items, total = await service.list(
        tenant_id=tenant_id,
        skip=skip,
        limit=limit,
        filters=filters,
        order_by=KnowledgeDocument.created_at.desc(),
    )

    return build_list_response(
        data=[_doc_to_response(d) for d in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


@router.get("/documents/{document_id}")
async def get_document(
    document_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single knowledge document with full content."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = KnowledgeService(db)
    doc = await service.get(document_id, tenant_id=tenant_id)
    return build_single_response(_doc_to_response(doc))


@router.patch("/documents/{document_id}")
async def update_document(
    document_id: UUID,
    body: DocumentUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a document's metadata.

    If ``content`` is provided, the document is automatically re-indexed
    in Qdrant (old chunks removed, new ones inserted).
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = KnowledgeService(db)

    updates = body.model_dump(exclude_unset=True)
    result = await service.update_document(tenant_id, document_id, **updates)

    # Fetch the updated document
    doc = await service.get(document_id, tenant_id=tenant_id)
    return build_single_response(_doc_to_response(doc))


@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a knowledge document from both the DB and Qdrant."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = KnowledgeService(db)
    await service.delete_document(tenant_id, document_id)
    return None


@router.post("/documents/{document_id}/index")
async def index_document(
    document_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger Qdrant indexing for a document.

    Chunks the document content, generates embeddings, and upserts into
    the tenant's Qdrant collection.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = KnowledgeService(db)
    result = await service.index_document(tenant_id, document_id)
    return build_single_response(result)


# ── Search ───────────────────────────────────────────────────────────────────


@router.post("/search")
async def search_documents(
    body: SearchQuery,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Semantic search across indexed documents.

    Accepts a natural language query and returns ranked results ranked
    by cosine similarity to the query embedding.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = KnowledgeService(db)

    # Build optional filters from search query parameters
    filters: dict[str, str] = {}
    if body.category:
        filters["category"] = body.category
    if body.doc_type:
        filters["doc_type"] = body.doc_type
    if body.tags:
        # Note: Qdrant tag filtering would need array contains logic;
        # for simplicity, we skip tag filtering at the Qdrant level
        # and let the caller post-filter if needed.
        pass

    results = await service.search(
        tenant_id=tenant_id,
        query=body.query,
        top_k=body.top_k,
        filters=filters or None,
    )

    # Apply threshold filter if specified
    if body.threshold is not None:
        results = [r for r in results if r["score"] >= body.threshold]

    search_results = [SearchResult(**r) for r in results]

    return build_single_response(
        SearchResponse(
            results=search_results,
            total=len(search_results),
            query=body.query,
        )
    )


# ── Collections ──────────────────────────────────────────────────────────────


@router.get("/collections/stats")
async def get_collection_stats(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get Qdrant collection statistics for the current tenant."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = KnowledgeService(db)
    stats = await service.get_collection_stats(tenant_id)
    return build_single_response(CollectionStatsResponse(tenant_id=tenant_id, **stats))


# ── Re-index ─────────────────────────────────────────────────────────────────


@router.post("/reindex")
async def reindex_all(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Bulk re-index all documents with ``is_indexed=False``."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = KnowledgeService(db)

    results = await service.reindex_all_unindexed(tenant_id)

    indexed = sum(1 for r in results if r.get("is_indexed", False))
    failed = sum(1 for r in results if not r.get("is_indexed", False))
    errors = [
        r.get("error", "")
        for r in results
        if not r.get("is_indexed", False) and r.get("error")
    ]

    return build_single_response(
        ReindexResponse(
            total_documents=len(results),
            indexed=indexed,
            failed=failed,
            errors=errors,
            message="Re-index complete"
            if not errors
            else f"Re-index finished with {failed} failure(s)",
        )
    )
