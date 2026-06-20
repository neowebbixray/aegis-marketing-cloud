"""
Application-level audit logging service for Aegis Marketing Cloud.

Records state-changing events (create, update, delete, login, logout, etc.)
in the ``audit_logs`` table.  The table is already provisioned by the database
migration ``0002_security_rls_audit_domain_tables.py`` with a PL/pgSQL trigger
for automatic row-level auditing.  This service provides a Python convenience
layer for logging semantic events that may not correspond 1:1 to database rows
(e.g. login, logout, API key creation).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import ClauseElement, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("amc.audit")

# ── Canonical event types ────────────────────────────────────────────────────
# These strings are stored in the ``action`` column and should be used
# consistently across the codebase.

EVENT_USER_LOGIN = "user.login"
EVENT_USER_LOGOUT = "user.logout"
EVENT_USER_CREATED = "user.created"
EVENT_USER_UPDATED = "user.updated"
EVENT_USER_DELETED = "user.deleted"
EVENT_USER_PASSWORD_CHANGED = "user.password_changed"

EVENT_CONTACT_CREATED = "contact.created"
EVENT_CONTACT_UPDATED = "contact.updated"
EVENT_CONTACT_DELETED = "contact.deleted"

EVENT_DEAL_CREATED = "deal.created"
EVENT_DEAL_UPDATED = "deal.updated"
EVENT_DEAL_DELETED = "deal.deleted"
EVENT_DEAL_STAGE_CHANGED = "deal.stage_changed"

EVENT_CAMPAIGN_CREATED = "campaign.created"
EVENT_CAMPAIGN_UPDATED = "campaign.updated"
EVENT_CAMPAIGN_DELETED = "campaign.deleted"

EVENT_PIPELINE_CREATED = "pipeline.created"
EVENT_PIPELINE_UPDATED = "pipeline.updated"
EVENT_PIPELINE_DELETED = "pipeline.deleted"

EVENT_API_KEY_CREATED = "api_key.created"
EVENT_API_KEY_REVOKED = "api_key.revoked"

EVENT_WEBHOOK_CREATED = "webhook.created"
EVENT_WEBHOOK_UPDATED = "webhook.updated"
EVENT_WEBHOOK_DELETED = "webhook.deleted"

EVENT_AI_AGENT_CREATED = "ai_agent.created"
EVENT_AI_AGENT_EXECUTED = "ai_agent.executed"

EVENT_BILLING_SUBSCRIPTION_CHANGED = "billing.subscription.changed"
EVENT_BILLING_INVOICE_CREATED = "billing.invoice.created"

EVENT_TENANT_CREATED = "tenant.created"
EVENT_TENANT_UPDATED = "tenant.updated"

EVENT_SETTINGS_CHANGED = "settings.changed"
EVENT_FEATURE_FLAG_TOGGLED = "feature_flag.toggled"

# ── All recognised event types (used for validation) ─────────────────────────
ALL_EVENT_TYPES: set[str] = {
    value
    for name, value in list(globals().items())
    if name.startswith("EVENT_")
}


def _compute_changes(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
) -> list[str] | None:
    """Return sorted list of field names that differ between two dicts.

    Only top-level keys are compared; nested objects are stringified first.
    Returns ``None`` when either dict is ``None``.
    """
    if before is None or after is None:
        return None
    changed: list[str] = []
    all_keys = set(before) | set(after)
    for key in sorted(all_keys):
        b = before.get(key)
        a = after.get(key)
        # Normalise serialisable types for comparison
        try:
            b_json = json.dumps(b, sort_keys=True, default=str)
            a_json = json.dumps(a, sort_keys=True, default=str)
        except (TypeError, ValueError):
            continue
        if b_json != a_json:
            changed.append(key)
    return changed if changed else None


class AuditLogService:
    """Service for recording and querying audit log entries.

    Usage::

        audit = AuditLogService(db)
        await audit.log_event(
            actor_id=user.id,
            action=EVENT_CONTACT_CREATED,
            resource_type="contact",
            resource_id=contact.id,
            changes={"company": None, "company": "Acme Corp"},
            workspace_id=workspace_id,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0 ...",
        )
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def log_event(
        self,
        *,
        actor_id: str | UUID | None,
        action: str,
        resource_type: str,
        resource_id: str | UUID | None = None,
        changes: dict[str, tuple[Any, Any]] | dict[str, Any] | None = None,
        workspace_id: str | UUID | None = None,
        tenant_id: str | UUID | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> UUID:
        """Record a single audit event in the ``audit_logs`` table.

        Args:
            actor_id:   UUID (or string) of the user who performed the action.
            action:     One of the ``EVENT_*`` constants defined above.
            resource_type: Human-readable resource type (e.g. ``contact``).
            resource_id:   UUID of the affected resource (if applicable).
            changes:    For **update** events, a dict of ``{field_name: (old, new)}``.
                        For **create** events, a dict of ``{field_name: value}``.
                        Pass ``None`` if no change detail is available.
            workspace_id: The workspace scope (optional).
            tenant_id:    The tenant scope (optional).
            ip_address:   Client IP address (optional).
            user_agent:   Client User-Agent header (optional).
            request_id:   ``X-Request-ID`` value for correlation (optional).
            metadata:     Extra structured data to store with the event.

        Returns:
            The UUID of the newly created audit log entry.

        Raises:
            ValueError: If ``action`` is not a recognised event type.
        """
        if action not in ALL_EVENT_TYPES:
            logger.warning("Unrecognised audit event type: %s", action)

        # Normalise ``changes`` into ``old_values`` / ``new_values`` JSONB
        old_values: dict[str, Any] | None = None
        new_values: dict[str, Any] | None = None
        changed_fields: list[str] | None = None

        if changes is not None:
            # Determine if changes is ``{field: (old, new)}`` or ``{field: value}``
            sample_val = next(iter(changes.values()), None)
            if (
                isinstance(sample_val, (list, tuple))
                and len(sample_val) == 2
            ):
                # Update-style: {field: (old, new)}
                old_values = {}
                new_values = {}
                for field, (old, new) in changes.items():
                    old_values[field] = old
                    new_values[field] = new
                changed_fields = _compute_changes(old_values, new_values)
            else:
                # Create-style: {field: value}
                new_values = dict(changes)
                old_values = None
                changed_fields = list(changes.keys()) if changes else None

        # Merge metadata into new_values if present
        if metadata:
            new_values = {**(new_values or {}), "_metadata": metadata}

        actor_id_str: str | None = str(actor_id) if actor_id else None
        resource_id_str: str | None = str(resource_id) if resource_id else None
        workspace_id_str: str | None = str(workspace_id) if workspace_id else None
        tenant_id_str: str | None = str(tenant_id) if tenant_id else None

        stmt = text("""
            INSERT INTO audit_logs (
                tenant_id, workspace_id, user_id, action,
                entity_type, entity_id, old_values, new_values,
                changed_fields, ip_address, user_agent, request_id
            ) VALUES (
                :tenant_id::uuid, :workspace_id::uuid, :actor_id::uuid,
                :action, :entity_type, :entity_id::uuid,
                :old_values::jsonb, :new_values::jsonb,
                :changed_fields::text[], :ip_address, :user_agent, :request_id
            )
            RETURNING id
        """)

        result = await self.db.execute(
            stmt,
            {
                "tenant_id": tenant_id_str,
                "workspace_id": workspace_id_str,
                "actor_id": actor_id_str,
                "action": action,
                "entity_type": resource_type,
                "entity_id": resource_id_str,
                "old_values": json.dumps(old_values) if old_values else None,
                "new_values": json.dumps(new_values) if new_values else None,
                "changed_fields": changed_fields,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "request_id": request_id,
            },
        )
        row = result.fetchone()
        entry_id: UUID = row[0] if row else UUID(int=0)
        logger.debug(
            "Audit log: %s %s %s id=%s",
            actor_id_str,
            action,
            resource_type,
            entry_id,
        )
        return entry_id

    async def get_events(
        self,
        *,
        actor_id: str | UUID | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_id: str | UUID | None = None,
        workspace_id: str | UUID | None = None,
        tenant_id: str | UUID | None = None,
        limit: int = 100,
        offset: int = 0,
        order_desc: bool = True,
    ) -> list[dict[str, Any]]:
        """Query audit log entries with optional filters.

        Returns a list of matching audit log rows, most recent first by default.
        """
        clauses: list[str] = ["1=1"]
        params: dict[str, Any] = {}

        if actor_id:
            clauses.append("user_id = :actor_id::uuid")
            params["actor_id"] = str(actor_id)
        if action:
            clauses.append("action = :action")
            params["action"] = action
        if resource_type:
            clauses.append("entity_type = :entity_type")
            params["entity_type"] = resource_type
        if resource_id:
            clauses.append("entity_id = :resource_id::uuid")
            params["resource_id"] = str(resource_id)
        if workspace_id:
            clauses.append("workspace_id = :workspace_id::uuid")
            params["workspace_id"] = str(workspace_id)
        if tenant_id:
            clauses.append("tenant_id = :tenant_id::uuid")
            params["tenant_id"] = str(tenant_id)

        order = "DESC" if order_desc else "ASC"

        stmt = text(f"""
            SELECT
                id, tenant_id, workspace_id, user_id, action,
                entity_type, entity_id, old_values, new_values,
                changed_fields, ip_address, user_agent, request_id,
                created_at
            FROM audit_logs
            WHERE {' AND '.join(clauses)}
            ORDER BY created_at {order}
            LIMIT :limit OFFSET :offset
        """)

        params["limit"] = limit
        params["offset"] = offset

        result = await self.db.execute(stmt, params)
        rows = result.fetchall()

        return [
            {
                "id": str(row.id),
                "tenant_id": str(row.tenant_id) if row.tenant_id else None,
                "workspace_id": str(row.workspace_id) if row.workspace_id else None,
                "actor_id": str(row.user_id) if row.user_id else None,
                "action": row.action,
                "resource_type": row.entity_type,
                "resource_id": str(row.entity_id) if row.entity_id else None,
                "old_values": row.old_values,
                "new_values": row.new_values,
                "changed_fields": row.changed_fields,
                "ip_address": row.ip_address,
                "user_agent": row.user_agent,
                "request_id": row.request_id,
                "created_at": (
                    row.created_at.isoformat()
                    if isinstance(row.created_at, datetime)
                    else str(row.created_at)
                ),
            }
            for row in rows
        ]

    async def count_events(self, **kwargs: Any) -> int:
        """Return the count of matching audit events (same filters as
        ``get_events``)."""
        clauses: list[str] = ["1=1"]
        params: dict[str, Any] = {}

        for key, param_name, col in [
            ("actor_id", "actor_id", "user_id"),
            ("action", "action", "action"),
            ("resource_type", "entity_type", "entity_type"),
            ("resource_id", "resource_id", "entity_id"),
            ("workspace_id", "workspace_id", "workspace_id"),
            ("tenant_id", "tenant_id", "tenant_id"),
        ]:
            val = kwargs.get(key)
            if val:
                clauses.append(f"{col} = :{param_name}::uuid")
                params[param_name] = str(val)

        stmt = text(f"""
            SELECT COUNT(*) FROM audit_logs
            WHERE {' AND '.join(clauses)}
        """)
        result = await self.db.execute(stmt, params)
        return result.scalar() or 0
