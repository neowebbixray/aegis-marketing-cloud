"""
Media service: file upload/download via MinIO (with local filesystem fallback),
asset CRUD, thumbnail generation, and streaming responses.
"""

from __future__ import annotations

import hashlib
import io
import logging
import mimetypes
import os
import uuid
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.core.file_validator import FileCategory, validate_file
from app.models.media import Asset
from app.services.base import BaseService

logger = logging.getLogger("amc.services.media")

# ── Storage backend constants ────────────────────────────────────────────────
STORAGE_BACKEND_MINIO = "minio"
STORAGE_BACKEND_LOCAL = "local"

# ── Thumbnail cache directory ────────────────────────────────────────────────
THUMBNAIL_DIR = Path(settings.media_library_root or "media-library") / ".thumbnails"

# ── Supported image MIME types for thumbnail generation ──────────────────────
IMAGE_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

# ── MinIO client (lazy-initialised) ──────────────────────────────────────────
_minio_client: Any | None = None
_minio_available: bool | None = None


def _get_minio_client():
    """Return a MinIO client, or ``None`` if MinIO is unavailable.

    The client is initialised once and cached.  If initialisation fails all
    subsequent calls return ``None`` so the service falls back to local storage.
    """
    global _minio_client, _minio_available
    if _minio_available is False:
        return None
    if _minio_client is not None:
        return _minio_client

    endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    use_ssl = os.getenv("MINIO_USE_SSL", "false").lower() == "true"

    try:
        from minio import Minio

        client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=use_ssl,
        )
        # Verify connectivity
        client.list_buckets()
        _minio_client = client
        _minio_available = True
        logger.info("MinIO client initialised at %s", endpoint)
        return _minio_client
    except Exception as exc:
        logger.warning(
            "MinIO unavailable at %s — falling back to local storage: %s",
            endpoint,
            exc,
        )
        _minio_available = False
        return None


# ── Helper: get bucket name ──────────────────────────────────────────────────
_ASSET_BUCKET = os.getenv("MINIO_ASSET_BUCKET", "assets")
_MEDIA_BUCKET = os.getenv("MINIO_MEDIA_BUCKET", "media")


def _ensure_bucket(client: Any, bucket: str) -> None:
    """Create *bucket* if it does not already exist."""
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("Created MinIO bucket: %s", bucket)
    except Exception:
        logger.debug("Bucket %s already exists or could not be created", bucket)


# ── Media Service ────────────────────────────────────────────────────────────


class MediaService(BaseService[Asset]):
    """CRUD and file I/O for Asset records backed by MinIO or local storage."""

    model = Asset

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)
        self._minio = _get_minio_client()

    # ── Initialisation helpers ───────────────────────────────────────────────

    def _storage_root(self) -> Path:
        """Return the local filesystem root for media files."""
        return Path(settings.media_library_root or "media-library")

    def _local_path(self, storage_path: str) -> Path:
        """Resolve a relative storage path to an absolute local path."""
        return self._storage_root() / storage_path

    # ── Upload ───────────────────────────────────────────────────────────────

    async def upload_file(
        self,
        tenant_id: UUID,
        user_id: UUID,
        file: Any,  # Supports UploadFile or file-like objects
        category: str | None = None,
        alt_text: str | None = None,
        is_public: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> Asset:
        """Stream *file* to storage and create an Asset record.

        Parameters
        ----------
        tenant_id
            Owning tenant.
        user_id
            Uploading user.
        file
            A FastAPI ``UploadFile`` or any file-like object with ``.filename``,
            ``.content_type`` (optional), ``.read()`` / ``.file``.
        category, alt_text, is_public, metadata
            Asset metadata stored alongside the record.

        Returns
        -------
        Asset
            The newly created Asset record.
        """
        # Read file content
        content = await file.read()
        size_bytes = len(content)

        # ── File validation ─────────────────────────────────────────────────
        original_filename = getattr(file, "filename", None) or "unnamed"
        client_content_type = getattr(file, "content_type", None)

        validation = validate_file(
            file_bytes=content,
            filename=original_filename,
            content_type=client_content_type,
        )
        if not validation.is_valid:
            raise ValidationException(detail=validation.error)

        # Use validated MIME type and category
        mime_type = validation.mime_type or (
            client_content_type
            or mimetypes.guess_type(original_filename)[0]
            or "application/octet-stream"
        )
        validated_category = validation.category.value if validation.category else None

        # Determine filename and MIME type
        filename = f"{uuid.uuid4().hex}_{original_filename}"

        # Compute checksum (SHA-256)
        checksum = hashlib.sha256(content).hexdigest()

        # Determine image dimensions (if applicable)
        width, height = await self._get_image_dimensions(content, mime_type)

        # Build storage path: tenant_id/category/filename
        effective_category = validated_category or category or "uncategorised"
        storage_path = f"{tenant_id}/{effective_category}/{filename}"

        # Persist to storage backend
        if self._minio is not None:
            storage_backend = STORAGE_BACKEND_MINIO
            bucket = _MEDIA_BUCKET
            _ensure_bucket(self._minio, bucket)
            self._minio.put_object(
                bucket,
                storage_path,
                io.BytesIO(content),
                length=size_bytes,
                content_type=mime_type,
            )
        else:
            storage_backend = STORAGE_BACKEND_LOCAL
            local_path = self._local_path(storage_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            local_path.write_bytes(content)

        # Create database record
        asset = await self.create(
            tenant_id=tenant_id,
            user_id=user_id,
            filename=filename,
            original_filename=original_filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            storage_path=storage_path,
            storage_backend=storage_backend,
            category=effective_category if effective_category != "uncategorised" else category,
            alt_text=alt_text,
            width=width,
            height=height,
            metadata=metadata or {},
            is_public=is_public,
            checksum=checksum,
        )

        logger.info(
            "Uploaded asset %s (%s, %d bytes) for tenant %s",
            asset.id,
            original_filename,
            size_bytes,
            tenant_id,
        )
        return asset

    async def _get_image_dimensions(
        self, content: bytes, mime_type: str
    ) -> tuple[int | None, int | None]:
        """Return ``(width, height)`` for image content, or ``(None, None)``."""
        if mime_type not in IMAGE_MIME_TYPES:
            return None, None
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(content))
            return img.width, img.height
        except ImportError:
            logger.debug("Pillow not installed — skipping dimension detection")
            return None, None
        except Exception:
            logger.debug("Could not determine image dimensions", exc_info=True)
            return None, None

    # ── Download URL ─────────────────────────────────────────────────────────

    async def get_download_url(
        self,
        asset_id: UUID,
        tenant_id: UUID,
        expires_in: int = 3600,
    ) -> str:
        """Generate a presigned download URL for the asset.

        For MinIO-backed assets this returns a presigned GET URL.  For local-
        storage assets a direct ``/api/v1/media/{id}/download`` URL is returned
        instead (the caller should stream via ``serve_file``).
        """
        asset = await self.get(asset_id, tenant_id=tenant_id)

        if asset.storage_backend == STORAGE_BACKEND_MINIO and self._minio is not None:
            bucket = _MEDIA_BUCKET
            url = self._minio.presigned_get_object(
                bucket,
                asset.storage_path,
                expires=expires_in,
            )
            return url

        # Local storage: return a relative API path
        # The actual file is served through serve_file()
        return f"/api/v1/media/{asset.id}/download"

    # ── List ─────────────────────────────────────────────────────────────────

    async def list_assets(
        self,
        tenant_id: UUID,
        category: str | None = None,
        mime_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[list[Asset], int]:
        """Paginated list of assets with optional filters."""
        filters = []

        if category:
            filters.append(Asset.category == category)
        if mime_type:
            filters.append(Asset.mime_type == mime_type)
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    Asset.original_filename.ilike(pattern),
                    Asset.filename.ilike(pattern),
                    Asset.alt_text.ilike(pattern),
                )
            )

        skip = (page - 1) * per_page
        return await self.list(
            tenant_id=tenant_id,
            skip=skip,
            limit=per_page,
            filters=filters or None,
            order_by=Asset.created_at.desc(),
        )

    # ── Get ─────────────────────────────────────────────────────────────────

    async def get_asset(self, asset_id: UUID, tenant_id: UUID) -> Asset:
        """Fetch a single asset by ID."""
        return await self.get(asset_id, tenant_id=tenant_id)

    # ── Delete ───────────────────────────────────────────────────────────────

    async def delete_asset(self, asset_id: UUID, tenant_id: UUID) -> None:
        """Remove file from storage and soft-delete the database record."""
        asset = await self.get(asset_id, tenant_id=tenant_id)

        # Remove from storage backend
        await self._remove_from_storage(asset)

        # Soft-delete the DB record
        await self.soft_delete(asset_id, tenant_id=tenant_id)

        logger.info("Deleted asset %s for tenant %s", asset_id, tenant_id)

    async def _remove_from_storage(self, asset: Asset) -> None:
        """Delete the underlying file from MinIO or local filesystem."""
        if asset.storage_backend == STORAGE_BACKEND_MINIO and self._minio is not None:
            try:
                self._minio.remove_object(_MEDIA_BUCKET, asset.storage_path)
            except Exception as exc:
                logger.warning(
                    "Failed to remove MinIO object %s: %s",
                    asset.storage_path,
                    exc,
                )
        else:
            local_path = self._local_path(asset.storage_path)
            if local_path.exists():
                local_path.unlink()

    # ── Update ───────────────────────────────────────────────────────────────

    async def update_asset(
        self,
        asset_id: UUID,
        tenant_id: UUID,
        **updates: Any,
    ) -> Asset:
        """Update asset metadata fields."""
        # Only allow updating metadata fields, not storage paths
        allowed_keys = {"category", "alt_text", "is_public", "metadata"}
        filtered = {k: v for k, v in updates.items() if k in allowed_keys}
        return await self.update(asset_id, tenant_id=tenant_id, **filtered)

    # ── Thumbnail ────────────────────────────────────────────────────────────

    async def get_asset_thumbnail(
        self,
        asset_id: UUID,
        tenant_id: UUID,
        width: int = 200,
        height: int = 200,
    ) -> tuple[bytes, str]:
        """Generate (or retrieve cached) thumbnail for an image asset.

        Returns
        -------
        Tuple of ``(image_bytes, mime_type)``.
        """
        asset = await self.get(asset_id, tenant_id=tenant_id)

        if asset.mime_type not in IMAGE_MIME_TYPES:
            raise ValidationException(
                detail=f"Thumbnails are not supported for {asset.mime_type} assets"
            )

        # Cached thumbnail path
        thumb_filename = (
            f"{asset.id}_{width}x{height}_{asset.checksum or 'nocache'}.webp"
        )
        thumb_dir = THUMBNAIL_DIR / str(tenant_id)
        thumb_dir.mkdir(parents=True, exist_ok=True)
        thumb_path = thumb_dir / thumb_filename

        # Return cached thumbnail
        if thumb_path.exists():
            return thumb_path.read_bytes(), "image/webp"

        # Load original image
        original_bytes = await self._read_asset_content(asset)
        try:
            from PIL import Image, WebPImagePlugin  # noqa: F401 — ensure WebP support

            img = Image.open(io.BytesIO(original_bytes))
            img.thumbnail((width, height), Image.LANCZOS)

            # Convert to RGB if necessary (WebP does not support RGBA with all decoders)
            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
            else:
                img = img.convert("RGB")

            buf = io.BytesIO()
            img.save(buf, format="WEBP", quality=80, optimize=True)
            thumb_bytes = buf.getvalue()

            # Cache to disk
            thumb_path.write_bytes(thumb_bytes)

            return thumb_bytes, "image/webp"
        except ImportError:
            # Fallback: return original if Pillow not available
            logger.warning("Pillow not installed — returning original for thumbnail")
            return original_bytes, asset.mime_type

    async def _read_asset_content(self, asset: Asset) -> bytes:
        """Read the full content of an asset from storage."""
        if asset.storage_backend == STORAGE_BACKEND_MINIO and self._minio is not None:
            response = self._minio.get_object(_MEDIA_BUCKET, asset.storage_path)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        else:
            local_path = self._local_path(asset.storage_path)
            if not local_path.exists():
                raise NotFoundException(detail="Asset file not found on disk")
            return local_path.read_bytes()

    # ── Serve file ───────────────────────────────────────────────────────────

    async def serve_file(
        self,
        asset_id: UUID,
        tenant_id: UUID,
    ) -> tuple[bytes, str, str]:
        """Return raw bytes, mime type, and filename for streaming an asset.

        For MinIO-backed assets this reads the object into memory; for local
        assets it reads from disk.  The caller should wrap the result in a
        ``StreamingResponse``.
        """
        asset = await self.get(asset_id, tenant_id=tenant_id)
        content = await self._read_asset_content(asset)
        return content, asset.mime_type, asset.original_filename

    # ── Batch delete ─────────────────────────────────────────────────────────

    async def batch_delete(
        self,
        tenant_id: UUID,
        asset_ids: list[UUID],
    ) -> tuple[int, list[UUID]]:
        """Delete multiple assets by ID.  Returns ``(deleted_count, deleted_ids)``."""
        deleted_ids: list[UUID] = []
        for asset_id in asset_ids:
            try:
                await self.delete_asset(asset_id, tenant_id)
                deleted_ids.append(asset_id)
            except NotFoundException:
                logger.debug("Asset %s not found during batch delete — skipping", asset_id)
            except Exception as exc:
                logger.error("Failed to delete asset %s: %s", asset_id, exc)

        return len(deleted_ids), deleted_ids
