"""
CRM service: contacts, deals, pipelines, activities CRUD and business logic.
"""

from __future__ import annotations

import csv
import io
import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.exceptions import NotFoundException, ValidationException
from app.models.crm import Activity, Contact, Deal, Pipeline, PipelineStage
from app.services.base import BaseService

logger = logging.getLogger("amc.services.crm")


class ContactService(BaseService[Contact]):
    """CRUD and search for Contact records."""

    model = Contact

    async def search(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        query: str,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Contact], int]:
        """Full-text search across contact name, email, company, and phone."""
        search_pattern = f"%{query}%"
        filters = [
            or_(
                Contact.first_name.ilike(search_pattern),
                Contact.last_name.ilike(search_pattern),
                Contact.email.ilike(search_pattern),
                Contact.company.ilike(search_pattern),
                Contact.phone.ilike(search_pattern),
            ),
            Contact.workspace_id == workspace_id,
        ]
        return await self.list(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            filters=filters,
        )

    async def import_csv(
        self, tenant_id: UUID, workspace_id: UUID, csv_content: str, owner_id: UUID | None = None
    ) -> int:
        """Bulk-import contacts from a CSV string.

        Expected columns: first_name, last_name, email, phone, company, position,
        lifecycle_stage, source, tags.

        Returns the number of imported contacts.
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        count = 0
        for row in reader:
            tags = [t.strip() for t in row.pop("tags", "").split(",") if t.strip()] if row.get("tags") else None
            contact = Contact(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                first_name=row.get("first_name", ""),
                last_name=row.get("last_name", ""),
                email=row.get("email"),
                phone=row.get("phone"),
                company=row.get("company"),
                position=row.get("position"),
                lifecycle_stage=row.get("lifecycle_stage", "lead"),
                source=row.get("source"),
                tags=tags,
                owner_id=owner_id,
            )
            self.db.add(contact)
            count += 1
        await self.db.flush()
        await self.db.commit()
        logger.info("Imported %d contacts for workspace %s", count, workspace_id)
        return count

    async def export_csv(self, tenant_id: UUID, workspace_id: UUID) -> str:
        """Export contacts as CSV string."""
        items, _ = await self.list(tenant_id=tenant_id, filters=[Contact.workspace_id == workspace_id])
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["first_name", "last_name", "email", "phone", "company", "position",
                         "lifecycle_stage", "source", "tags"])
        for c in items:
            tags = ",".join(c.tags) if c.tags else ""
            writer.writerow([c.first_name, c.last_name, c.email, c.phone, c.company,
                             c.position, c.lifecycle_stage, c.source or "", tags])
        return output.getvalue()


class DealService(BaseService[Deal]):
    """CRUD and stage management for Deal records."""

    model = Deal

    async def move_stage(
        self,
        deal_id: UUID,
        new_stage_id: UUID,
        tenant_id: UUID,
        reason: str | None = None,
    ) -> Deal:
        """Move a deal to a different pipeline stage with validation.

        Validates that the new stage belongs to the same pipeline as the
        deal's current stage.
        """
        deal = await self.get(deal_id, tenant_id=tenant_id)

        # Verify the new stage exists
        stage_result = await self.db.execute(
            select(PipelineStage).where(PipelineStage.id == new_stage_id)
        )
        new_stage = stage_result.scalars().first()
        if new_stage is None:
            raise NotFoundException(detail="Pipeline stage not found")

        # Verify the stage belongs to the same pipeline
        if deal.pipeline_stage_id:
            old_stage_result = await self.db.execute(
                select(PipelineStage).where(PipelineStage.id == deal.pipeline_stage_id)
            )
            old_stage = old_stage_result.scalars().first()
            if old_stage and old_stage.pipeline_id != new_stage.pipeline_id:
                raise ValidationException(
                    detail="Cannot move deal to a stage in a different pipeline"
                )

        old_stage_id = deal.pipeline_stage_id
        deal.pipeline_stage_id = new_stage_id
        if new_stage.probability is not None:
            deal.probability = new_stage.probability

        await self.db.flush()
        await self.db.commit()
        await self.db.refresh(deal)

        logger.info(
            "Deal %s moved from stage %s to stage %s%s",
            deal_id,
            old_stage_id,
            new_stage_id,
            f" — reason: {reason}" if reason else "",
        )
        return deal


class PipelineService(BaseService[Pipeline]):
    """CRUD for Pipeline and PipelineStage records."""

    model = Pipeline

    async def create_with_stages(
        self,
        tenant_id: UUID,
        workspace_id: UUID,
        name: str,
        description: str | None = None,
        is_default: bool = False,
        stages: list[dict[str, Any]] | None = None,
    ) -> Pipeline:
        """Create a pipeline with optional stages."""
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
            for idx, stage_data in enumerate(stages):
                stage = PipelineStage(
                    pipeline_id=pipeline.id,
                    name=stage_data.get("name", f"Stage {idx + 1}"),
                    order=stage_data.get("order", idx),
                    probability=stage_data.get("probability"),
                    colour=stage_data.get("colour"),
                )
                self.db.add(stage)
            await self.db.flush()

        await self.db.commit()
        await self.db.refresh(pipeline)
        return pipeline

    async def get_with_stages(self, pipeline_id: UUID) -> Pipeline:
        """Fetch a pipeline with its stages eagerly loaded."""
        result = await self.db.execute(
            select(Pipeline)
            .options(joinedload(Pipeline.stages))
            .where(Pipeline.id == pipeline_id)
        )
        pipeline = result.scalars().first()
        if pipeline is None:
            raise NotFoundException(detail="Pipeline not found")
        return pipeline


class ActivityService(BaseService[Activity]):
    """CRUD for Activity records."""

    model = Activity
