"""Media router: upload, download, thumbnail, and manage digital assets.

All list responses use the docs-mandated ``{data, meta, links}`` envelope.
All single-resource responses use ``{data: {...}}``.
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db, get_tenant_context
from app.models.auth import User
from app.schemas.base import build_list_response, build_single_response
from app.schemas.media import (
    AssetResponse,
    AssetUpdate,
    BatchDeleteRequest,
    BatchDeleteResponse,
    DownloadUrlResponse,
)
from app.services.media import MediaService

logger = logging.getLogger("amc.api.v1.media")

router = APIRouter(prefix="/media", tags=["media"])


# ── Upload (single file) ─────────────────────────────────────────────────────


@router.post("/upload", status_code=201)
async def upload_media(
    request: Request,
    file: UploadFile = File(...),
    category: str | None = Form(None),
    alt_text: str | None = Form(None),
    is_public: bool = Form(False),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload a single media file.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = MediaService(db)
    asset = await service.upload_file(
        tenant_id=tenant_id,
        user_id=current_user.id,
        file=file,
        category=category,
        alt_text=alt_text,
        is_public=is_public,
    )
    return build_single_response(AssetResponse.model_validate(asset))


# ── Upload (multiple files) ──────────────────────────────────────────────────


@router.post("/upload-multiple", status_code=201)
async def upload_media_multiple(
    request: Request,
    files: list[UploadFile] = File(...),
    category: str | None = Form(None),
    alt_text: str | None = Form(None),
    is_public: bool = Form(False),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Upload multiple media files at once.

    Returns the docs-mandated ``{data: [...]}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = MediaService(db)
    assets = []
    for file in files:
        asset = await service.upload_file(
            tenant_id=tenant_id,
            user_id=current_user.id,
            file=file,
            category=category,
            alt_text=alt_text,
            is_public=is_public,
        )
        assets.append(AssetResponse.model_validate(asset))
    return {"data": assets}


# ── List assets ──────────────────────────────────────────────────────────────


@router.get("")
async def list_media(
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    category: str | None = Query(None, max_length=50),
    mime_type: str | None = Query(None, max_length=100),
    search: str | None = Query(None, min_length=1, max_length=256),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List media assets with optional filtering.

    Returns the docs-mandated ``{data, meta, links}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = MediaService(db)
    items, total = await service.list_assets(
        tenant_id=tenant_id,
        category=category,
        mime_type=mime_type,
        search=search,
        page=page,
        per_page=limit,
    )
    return build_list_response(
        data=[AssetResponse.model_validate(a) for a in items],
        total=total,
        page=page,
        per_page=limit,
        request=request,
    )


# ── Get single asset ─────────────────────────────────────────────────────────


@router.get("/{asset_id}")
async def get_media(
    asset_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a single media asset.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = MediaService(db)
    asset = await service.get_asset(asset_id, tenant_id=tenant_id)
    return build_single_response(AssetResponse.model_validate(asset))


# ── Download / stream ────────────────────────────────────────────────────────


@router.get("/{asset_id}/download")
async def download_media(
    asset_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Download a media asset (streams file or redirects to presigned URL).

    For MinIO-backed assets this returns a presigned URL redirect.
    For local-storage assets this streams the file directly.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = MediaService(db)
    asset = await service.get_asset(asset_id, tenant_id=tenant_id)

    # MinIO-backed -> redirect to presigned URL
    if asset.storage_backend == "minio":
        url = await service.get_download_url(asset_id, tenant_id)
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url=url)

    # Local storage -> stream directly
    content, mime_type, filename = await service.serve_file(asset_id, tenant_id)
    return StreamingResponse(
        iter([content]),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(content)),
        },
    )


# ── Download URL (presigned) ─────────────────────────────────────────────────


@router.get("/{asset_id}/download-url")
async def get_media_download_url(
    asset_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    expires_in: int = Query(3600, ge=60, le=86400),
) -> dict:
    """Get a presigned download URL for a media asset.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = MediaService(db)
    url = await service.get_download_url(asset_id, tenant_id, expires_in=expires_in)
    asset = await service.get_asset(asset_id, tenant_id=tenant_id)
    return build_single_response(
        DownloadUrlResponse(
            url=url,
            expires_in=expires_in,
            filename=asset.original_filename,
            mime_type=asset.mime_type,
        ),
    )


# ── Thumbnail ────────────────────────────────────────────────────────────────


@router.get("/{asset_id}/thumbnail")
async def get_media_thumbnail(
    asset_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    width: int = Query(200, ge=16, le=4096),
    height: int = Query(200, ge=16, le=4096),
) -> Response:
    """Get a resized thumbnail of a media asset.

    Only supported for image MIME types.  Returns a WebP image.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = MediaService(db)
    thumb_bytes, mime_type = await service.get_asset_thumbnail(
        asset_id,
        tenant_id,
        width=width,
        height=height,
    )
    return Response(
        content=thumb_bytes,
        media_type=mime_type,
        headers={
            "Content-Disposition": "inline",
            "Cache-Control": "public, max-age=86400",
        },
    )


# ── Update ───────────────────────────────────────────────────────────────────


@router.patch("/{asset_id}")
async def update_media(
    asset_id: UUID,
    body: AssetUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update metadata on a media asset.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = MediaService(db)
    asset = await service.update_asset(
        asset_id,
        tenant_id=tenant_id,
        **body.model_dump(exclude_unset=True),
    )
    return build_single_response(AssetResponse.model_validate(asset))


# ── Delete (single) ──────────────────────────────────────────────────────────


@router.delete("/{asset_id}", status_code=204)
async def delete_media(
    asset_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a media asset and remove its file from storage."""
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = MediaService(db)
    await service.delete_asset(asset_id, tenant_id=tenant_id)


# ── Batch delete ─────────────────────────────────────────────────────────────


@router.delete("/batch")
async def batch_delete_media(
    body: BatchDeleteRequest,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Batch-delete multiple media assets.

    Returns the docs-mandated ``{data: {...}}`` envelope.
    """
    tenant_id = await get_tenant_context(request, current_user=current_user)
    service = MediaService(db)
    deleted_count, deleted_ids = await service.batch_delete(
        tenant_id=tenant_id,
        asset_ids=body.asset_ids,
    )
    return build_single_response(
        BatchDeleteResponse(
            deleted_count=deleted_count,
            asset_ids=deleted_ids,
        ),
    )
