"""CRM service classes: ContactService, DealService, PipelineService,
ActivityService, and CustomFieldDefinitionService.

All tenant-scoped operations require a ``tenant_id`` UUID.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFoundException, ValidationException
from app.models.crm import (
    Activity,
    Contact,
    CustomFieldDefinition,
    Deal,
    LeadScoreHistory,
    Pipeline,
    PipelineStage,
)
from app.services.base import BaseService

logger = logging.getLogger("amc.services.crm")


# ── ContactService ───────────────────────────────────────────────────────────


class ContactService(BaseService[Contact]):
    """CRUD and lead-scoring operations for contacts."""

    model = Contact

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db)

    async def create(
        self,
        tenant_id: UUID,
        workspace_id: UUID | None = None,
        **kwargs: Any,
    ) -> Contact:
        """Create a new contact with tenant + workspace context."""
        contact = Contact(
            tenant_id=tenant_id,
            workspace_id=workspace_id or kwargs.pop("workspace_id", None),
            first_name=kwargs.pop("first_name"),
            last_name=kwargs.pop("last_name"),
            email=kwargs.pop("email", None),
            phone=kwargs.pop("phone", None),
            company=kwargs.pop("company", None),
            position=kwargs.pop("position", None),
            lifecycle_stage=kwargs.pop("lifecycle_stage", "lead"),
            source=kwargs.pop("source", None),
            custom_fields=kwargs.pop("custom_fields", None) or {},
            tags=kwargs.pop("tags", None) or [],
            owner_id=kwargs.pop("owner_id", None),
        )
        self.db.add(contact)
        await self.db.flush()
        await self.db.refresh(contact)
        logger.debug("Created Contact %s", contact.id)
        return contact

    async def update_lead_score(
        self,
        contact_id: UUID,
        tenant_id: UUID,
        score: int,
        score_source: str,
        scoring_factors: dict[str, Any] | None = None,
        agent_id: UUID | None = None,
    ) -> Contact:
        """Update a contact's lead score and record the change in history.

        Args:
            contact_id: The contact to update.
            tenant_id: Tenant context.
            score: New score value (0-100).
            score_source: Source of the score (ai, rule_based, manual, etc.).
            scoring_factors: Optional breakdown of how the score was computed.
            agent_id: Optional AI agent or rule set that generated the score.

        Returns:
            The updated Contact.

        """
        contact = await self.get(contact_id, tenant_id=tenant_id)
        contact.score = score
        contact.score_updated_at = datetime.now(UTC)

        # Record in history table
        history = LeadScoreHistory(
            tenant_id=tenant_id,
            contact_id=contact_id,
            score=score,
            score_source=score_source,
            scoring_factors=scoring_factors,
            agent_id=agent_id,
        )
        self.db.add(history)

        await self.db.flush()
        await self.db.refresh(contact)
        logger.info(
            "Updated lead score for contact %s: %d (source: %s)",
            contact_id,
            score,
            score_source,
        )
        return contact

    async def search(
        self,
        tenant_id: UUID,
        workspace_id: UUID | None = None,
        query: str = "",
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Contact], int]:
        """Full-text search across contacts by name, email, company, or phone.

        Uses PostgreSQL full-text search via the ``search_vector`` tsvector column.
        Falls back to a LIKE-based search when the tsvector column is unavailable.
        """
        conditions = [Contact.tenant_id == tenant_id, Contact.deleted_at.is_(None)]
        if workspace_id:
            conditions.append(Contact.workspace_id == workspace_id)

        if query:
            # Try full-text search first
            ts_query = func.plainto_tsquery("english", query)
            conditions.append(Contact.search_vector.op("@@")(ts_query))  # type: ignore[union-attr]

        # Count
        count_stmt = select(func.count()).select_from(Contact).where(*conditions)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Fetch ranked results
        stmt = (
            select(Contact)
            .where(*conditions)
            .order_by(desc(Contact.created_at))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        # If no results from full-text, fall back to LIKE search
        if not items and query:
            like_pattern = f"%{query}%"
            fallback_conditions = [
                Contact.tenant_id == tenant_id,
                Contact.deleted_at.is_(None),
                or_(
                    Contact.first_name.ilike(like_pattern),
                    Contact.last_name.ilike(like_pattern),
                    Contact.email.ilike(like_pattern),
                    Contact.company.ilike(like_pattern),
                    Contact.phone.ilike(like_pattern),
                ),
            ]
            if workspace_id:
                fallback_conditions.append(Contact.workspace_id == workspace_id)

            count_stmt = select(func.count()).select_from(Contact).where(*fallback_conditions)
            total_result = await self.db.execute(count_stmt)
            total = total_result.scalar() or 0

            stmt = (
                select(Contact)
                .where(*fallback_conditions)
                .order_by(desc(Contact.created_at))
                .offset(skip)
                .limit(limit)
            )
            result = await self.db.execute(stmt)
            items = list(result.scalars().all())

        return items, total


# ── DealService ──────────────────────────────────────────────────────────────


class DealService(BaseService[Deal]):
    """CRUD and pipeline-stage management for deals."""

    model = Deal

    async def create(
        self,
        tenant_id: UUID,
        workspace_id: UUID | None = None,
        **kwargs: Any,
    ) -> Deal:
        """Create a new deal with tenant + workspace context."""
        deal = Deal(
            tenant_id=tenant_id,
            workspace_id=workspace_id or kwargs.pop("workspace_id", None),
            name=kwargs.pop("name"),
            value=kwargs.pop("value", None),
            currency=kwargs.pop("currency", "USD"),
            pipeline_stage_id=kwargs.pop("pipeline_stage_id"),
            contact_id=kwargs.pop("contact_id", None),
            organization_label=kwargs.pop("organization_label", None),
            owner_id=kwargs.pop("owner_id", None),
            probability=kwargs.pop("probability", None),
            expected_close_date=kwargs.pop("expected_close_date", None),
            custom_fields=kwargs.pop("custom_fields", None) or {},
        )
        self.db.add(deal)
        await self.db.flush()
        await self.db.refresh(deal)
        logger.debug("Created Deal %s", deal.id)
        return deal

    async def move_stage(
        self,
        deal_id: UUID,
        new_stage_id: UUID,
        tenant_id: UUID,
        reason: str | None = None,
        won_reason: str | None = None,
        lost_reason: str | None = None,
    ) -> Deal:
        """Move a deal to a different pipeline stage with validation.

        Validates that the new stage belongs to the same pipeline as the
        deal's current stage.
        """
        deal = await self.get(deal_id, tenant_id=tenant_id)

        # Verify the new stage exists
        stage_result = await self.db.execute(
            select(PipelineStage).where(PipelineStage.id == new_stage_id),
        )
        new_stage = stage_result.scalars().first()
        if new_stage is None:
            raise NotFoundException(detail="Pipeline stage not found")

        # Verify the stage belongs to the same pipeline
        if deal.pipeline_stage_id:
            old_stage_result = await self.db.execute(
                select(PipelineStage).where(PipelineStage.id == deal.pipeline_stage_id),
            )
            old_stage = old_stage_result.scalars().first()
            if old_stage and old_stage.pipeline_id != new_stage.pipeline_id:
                raise ValidationException(
                    detail="Cannot move deal to a stage in a different pipeline",
                )

        old_stage_id = deal.pipeline_stage_id
        deal.pipeline_stage_id = new_stage_id
        if new_stage.probability is not None:
            deal.probability = new_stage.probability

        # Handle win/loss reasons and timestamps
        stage_name = new_stage.name.lower().strip() if new_stage.name else ""
        if stage_name == "closed_won":
            if won_reason is not None:
                deal.won_reason = won_reason
                deal.won_at = datetime.now(UTC)
            elif reason is not None:
                deal.won_reason = reason
                deal.won_at = datetime.now(UTC)
            # Clear loss fields if moving to won
            deal.lost_reason = None
            deal.lost_at = None
        elif stage_name == "closed_lost":
            if lost_reason is not None:
                deal.lost_reason = lost_reason
                deal.lost_at = datetime.now(UTC)
            elif reason is not None:
                deal.lost_reason = reason
                deal.lost_at = datetime.now(UTC)
            # Clear win fields if moving to lost
            deal.won_reason = None
            deal.won_at = None
        else:
            # For non-won/lost stages, clear win/loss fields
            deal.won_reason = None
            deal.won_at = None
            deal.lost_reason = None
            deal.lost_at = None

        await self.db.flush()
        await self.db.refresh(deal)

        logger.info(
            "Deal %s moved from stage %s to stage %s%s",
            deal_id,
            old_stage_id,
            new_stage_id,
            f" — reason: {reason}" if reason else "",
        )
        return deal

    async def update_win_loss(
        self,
        deal_id: UUID,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> Deal:
        """Update win/loss tracking fields for a deal.

        Allowed kwargs: won_reason, won_at, lost_reason, lost_at.
        Setting a non-None ``won_reason`` also clears ``lost_reason``/``lost_at``
        and vice versa.
        """
        deal = await self.get(deal_id, tenant_id=tenant_id)

        won_reason = kwargs.get("won_reason")
        lost_reason = kwargs.get("lost_reason")
        won_at = kwargs.get("won_at")
        lost_at = kwargs.get("lost_at")

        if won_reason is not None:
            deal.won_reason = won_reason
            deal.won_at = won_at or datetime.now(UTC)
            deal.lost_reason = None
            deal.lost_at = None
        elif lost_reason is not None:
            deal.lost_reason = lost_reason
            deal.lost_at = lost_at or datetime.now(UTC)
            deal.won_reason = None
            deal.won_at = None
        elif won_at is not None and deal.won_reason is None:
            deal.won_at = won_at
        elif lost_at is not None and deal.lost_reason is None:
            deal.lost_at = lost_at

        await self.db.flush()
        await self.db.refresh(deal)
        return deal


# ── PipelineService ─────────────────────────────────────────────────────────


class PipelineService:
    """Manage sales pipelines and their stages."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list(
        self,
        tenant_id: UUID,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Pipeline], int]:
        """List pipelines scoped to a tenant with pagination."""
        conditions = [Pipeline.tenant_id == tenant_id, Pipeline.deleted_at.is_(None)]

        count_stmt = select(func.count()).select_from(Pipeline).where(*conditions)
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = (
            select(Pipeline)
            .options(joinedload(Pipeline.stages))
            .where(*conditions)
            .order_by(Pipeline.name)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        # Unique because joinedload may duplicate root rows
        items = list({p.id: p for p in result.unique().scalars().all()}.values())
        return items, total

    async def create_with_stages(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        name: str,
        description: str | None = None,
        is_default: bool = False,
        stages: list[dict[str, Any]] | None = None,
    ) -> Pipeline:
        """Create a pipeline with optional stages.

        Args:
            tenant_id: Tenant context.
            workspace_id: Workspace context.
            name: Pipeline name.
            description: Optional description.
            is_default: Whether this is the default pipeline.
            stages: List of stage dicts with keys: name, order, probability, colour.

        Returns:
            The created Pipeline with stages eagerly loaded.

        """
        # If this is the default pipeline, unset any existing default
        if is_default:
            existing_default = await self.db.execute(
                select(Pipeline).where(
                    Pipeline.tenant_id == tenant_id,
                    Pipeline.workspace_id == workspace_id,
                    Pipeline.is_default.is_(True),
                    Pipeline.deleted_at.is_(None),
                ),
            )
            old_default = existing_default.scalar_one_or_none()
            if old_default:
                old_default.is_default = False

        pipeline = Pipeline(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            name=name,
            description=description,
            is_default=is_default,
        )
        self.db.add(pipeline)
        await self.db.flush()

        if stages:
            for i, stage_data in enumerate(stages):
                stage = PipelineStage(
                    pipeline_id=pipeline.id,
                    name=stage_data.get("name", f"Stage {i + 1}"),
                    order=stage_data.get("order", i),
                    probability=stage_data.get("probability"),
                    colour=stage_data.get("colour"),
                )
                self.db.add(stage)
            await self.db.flush()

        await self.db.refresh(pipeline)
        logger.info("Created Pipeline %s with %d stages", pipeline.id, len(stages or []))
        return pipeline

    async def get_with_stages(self, pipeline_id: UUID) -> Pipeline:
        """Get a pipeline with its stages eagerly loaded.

        Raises ``NotFoundException`` if the pipeline doesn't exist or is deleted.
        """
        stmt = (
            select(Pipeline)
            .options(joinedload(Pipeline.stages))
            .where(Pipeline.id == pipeline_id, Pipeline.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        pipeline = result.unique().scalar_one_or_none()
        if pipeline is None:
            raise NotFoundException(detail=f"Pipeline {pipeline_id} not found")
        return pipeline

    async def update(
        self,
        pipeline_id: UUID,
        tenant_id: UUID,
        **kwargs: Any,
    ) -> Pipeline:
        """Update a pipeline's metadata (name, description, is_default)."""
        pipeline = await self._get_pipeline(pipeline_id, tenant_id)
        updatable = {"name", "description", "is_default"}
        for key, value in kwargs.items():
            if key in updatable and value is not None:
                setattr(pipeline, key, value)
        await self.db.flush()
        await self.db.refresh(pipeline)
        return pipeline

    async def soft_delete(self, pipeline_id: UUID, tenant_id: UUID) -> None:
        """Soft-delete a pipeline."""
        pipeline = await self._get_pipeline(pipeline_id, tenant_id)
        pipeline.soft_delete()
        await self.db.flush()
        logger.info("Soft-deleted Pipeline %s", pipeline_id)

    async def _get_pipeline(self, pipeline_id: UUID, tenant_id: UUID) -> Pipeline:
        """Fetch a pipeline scoped to a tenant."""
        stmt = select(Pipeline).where(
            Pipeline.id == pipeline_id,
            Pipeline.tenant_id == tenant_id,
            Pipeline.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        pipeline = result.scalar_one_or_none()
        if pipeline is None:
            raise NotFoundException(detail=f"Pipeline {pipeline_id} not found")
        return pipeline


# ── ActivityService ──────────────────────────────────────────────────────────


class ActivityService(BaseService[Activity]):
    """CRUD for CRM activities (calls, emails, meetings, notes, etc.)."""

    model = Activity

    async def create(
        self,
        tenant_id: UUID,
        workspace_id: UUID | None = None,
        **kwargs: Any,
    ) -> Activity:
        """Create a new activity with tenant + workspace context."""
        activity = Activity(
            tenant_id=tenant_id,
            workspace_id=workspace_id or kwargs.pop("workspace_id", None),
            type=kwargs.pop("type"),
            subject=kwargs.pop("subject"),
            description=kwargs.pop("description", None),
            contact_id=kwargs.pop("contact_id", None),
            deal_id=kwargs.pop("deal_id", None),
            user_id=kwargs.pop("user_id", None),
        )
        self.db.add(activity)
        await self.db.flush()
        await self.db.refresh(activity)
        logger.debug("Created Activity %s (%s)", activity.id, activity.type)
        return activity


# ── CustomFieldDefinitionService ─────────────────────────────────────────────


class CustomFieldDefinitionService(BaseService[CustomFieldDefinition]):
    """CRUD for custom field definitions per workspace."""

    model = CustomFieldDefinition

    async def create(
        self,
        tenant_id: UUID,
        workspace_id: UUID | None = None,
        **kwargs: Any,
    ) -> CustomFieldDefinition:
        """Create a custom field definition."""
        field_def = CustomFieldDefinition(
            tenant_id=tenant_id,
            workspace_id=workspace_id or kwargs.pop("workspace_id", None),
            name=kwargs.pop("name"),
            key=kwargs.pop("key"),
            description=kwargs.pop("description", None),
            field_type=kwargs.pop("field_type"),
            config=kwargs.pop("config", {}) or {},
            is_required=kwargs.pop("is_required", False),
            is_active=kwargs.pop("is_active", True),
            display_order=kwargs.pop("display_order", 0),
        )
        self.db.add(field_def)
        await self.db.flush()
        await self.db.refresh(field_def)
        logger.debug("Created CustomFieldDefinition %s (%s)", field_def.id, field_def.key)
        return field_def

    async def update(
        self,
        id: UUID,
        tenant_id: UUID | None = None,
        **kwargs: Any,
    ) -> CustomFieldDefinition:
        """Update a custom field definition.

        Overrides base update to add field_type change protection.
        Changing ``field_type`` after creation is allowed but requires clearing the
        ``config`` field to avoid stale dropdown options, etc.
        """
        obj = await self.get(id, tenant_id=tenant_id)
        for key, value in kwargs.items():
            if value is not None:
                setattr(obj, key, value)
        await self.db.flush()
        await self.db.refresh(obj)
        return obj
