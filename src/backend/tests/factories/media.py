"""Factory classes for media models:
Asset.
"""

from __future__ import annotations

import uuid

import factory
from app.models.media import Asset
from factory.alchemy import SQLAlchemyModelFactory


class BaseFactory(SQLAlchemyModelFactory):
    """Abstract base — defers flush to the test fixture."""

    class Meta:
        abstract = True
        sqlalchemy_session_persistence = None


class MediaAssetFactory(BaseFactory):
    """Generate realistic Asset (media) instances."""

    class Meta:
        model = Asset

    tenant_id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    filename = factory.LazyAttribute(
        lambda o: f"{uuid.uuid4().hex}_{o.original_filename}",
    )
    original_filename = factory.Faker("file_name")
    mime_type = factory.Iterator(
        [
            "image/jpeg",
            "image/png",
            "application/pdf",
            "video/mp4",
            "audio/mpeg",
        ]
    )
    size_bytes = factory.Faker("random_int", min=1024, max=10485760)
    storage_path = factory.LazyAttribute(
        lambda o: f"{o.tenant_id}/uncategorised/{o.filename}",
    )
    storage_backend = "local"
    category = factory.Iterator(["images", "documents", "videos", "marketing", None])
    alt_text = factory.Faker("sentence", nb_words=4)
    width = None
    height = None
    duration_seconds = None
    metadata = factory.Dict({"source": "factory"})
    is_public = False
    checksum = factory.Faker("sha256")
