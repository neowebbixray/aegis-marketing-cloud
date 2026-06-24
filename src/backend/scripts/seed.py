"""
Aegis Marketing Cloud — Development Seed Script
================================================

Seeds the development database with:
  - Default roles & permissions
  - Admin user (admin@aegismc.io / admin123)
  - Demo tenant & workspace
  - Sample: contacts, deals, pipelines, campaigns

Usage:
    python scripts/seed.py [--drop]

    By default, skips if data already exists (idempotent).
    Use --drop to drop all data first.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import UTC, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.core.security import hash_password
from app.database import Base, async_session_factory
from app.models.auth import User
from app.models.crm import Activity, Contact, Deal, Pipeline, PipelineStage
from app.models.tenant import (
    Permission,
    Role,
    RolePermission,
    Tenant,
    UserRole,
    Workspace,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def log(msg: str) -> None:
    """Emit a seed progress message to stdout."""
    sys.stdout.write(msg + "\n")


def utcnow() -> datetime:
    return datetime.now(UTC)


async def get_or_create(
    session: AsyncSession, model: type, filter_by: dict, defaults: dict | None = None
) -> tuple[object, bool]:
    """Fetch existing or create new. Returns (instance, created)."""
    stmt = select(model).filter_by(**filter_by)
    result = await session.execute(stmt)
    instance = result.scalar_one_or_none()
    if instance is not None:
        return instance, False
    kwargs = {**filter_by, **(defaults or {})}
    instance = model(**kwargs)
    session.add(instance)
    await session.flush()
    return instance, True


# ── Current timestamp for seed data ─────────────────────────────────────────

NOW = utcnow()
TENANT_ID = "00000000-0000-0000-0000-000000000001"
WORKSPACE_ID = "00000000-0000-0000-0000-000000000101"

PERMISSIONS = [
    {"code": "crm:contact:read", "name": "Read contacts", "group": "crm"},
    {"code": "crm:contact:create", "name": "Create contacts", "group": "crm"},
    {"code": "crm:contact:update", "name": "Update contacts", "group": "crm"},
    {"code": "crm:contact:delete", "name": "Delete contacts", "group": "crm"},
    {"code": "crm:deal:read", "name": "Read deals", "group": "crm"},
    {"code": "crm:deal:create", "name": "Create deals", "group": "crm"},
    {"code": "crm:deal:update", "name": "Update deals", "group": "crm"},
    {"code": "crm:deal:delete", "name": "Delete deals", "group": "crm"},
    {"code": "crm:pipeline:read", "name": "Read pipelines", "group": "crm"},
    {"code": "crm:pipeline:manage", "name": "Manage pipelines", "group": "crm"},
    {"code": "marketing:campaign:read", "name": "Read campaigns", "group": "marketing"},
    {"code": "marketing:campaign:create", "name": "Create campaigns", "group": "marketing"},
    {"code": "marketing:campaign:update", "name": "Update campaigns", "group": "marketing"},
    {"code": "marketing:campaign:delete", "name": "Delete campaigns", "group": "marketing"},
    {"code": "ai:agent:read", "name": "Read AI agents", "group": "ai"},
    {"code": "ai:agent:manage", "name": "Manage AI agents", "group": "ai"},
    {"code": "ai:conversation:read", "name": "Read conversations", "group": "ai"},
    {"code": "admin:workspace:manage", "name": "Manage workspaces", "group": "admin"},
    {"code": "admin:team:manage", "name": "Manage teams", "group": "admin"},
    {"code": "admin:billing:manage", "name": "Manage billing", "group": "admin"},
    {"code": "admin:settings:manage", "name": "Manage settings", "group": "admin"},
]

ROLES: dict[str, list[str]] = {
    "admin": [p["code"] for p in PERMISSIONS],
    "manager": [
        "crm:contact:read",
        "crm:contact:create",
        "crm:contact:update",
        "crm:deal:read",
        "crm:deal:create",
        "crm:deal:update",
        "crm:pipeline:read",
        "marketing:campaign:read",
        "marketing:campaign:create",
        "marketing:campaign:update",
        "ai:agent:read",
        "ai:conversation:read",
    ],
    "editor": [
        "crm:contact:read",
        "crm:contact:create",
        "crm:contact:update",
        "crm:deal:read",
        "crm:deal:create",
        "crm:deal:update",
        "crm:pipeline:read",
        "marketing:campaign:read",
        "marketing:campaign:create",
        "ai:conversation:read",
    ],
    "viewer": [
        "crm:contact:read",
        "crm:deal:read",
        "crm:pipeline:read",
        "marketing:campaign:read",
        "ai:conversation:read",
    ],
}

SAMPLE_CONTACTS = [
    {"first_name": "Alice", "last_name": "Johnson", "email": "alice@acme.com", "company": "Acme Corp", "score": 85, "tags": ["vip", "enterprise"], "job_title": "CEO"},
    {"first_name": "Bob", "last_name": "Smith", "email": "bob@globex.com", "company": "Globex Inc", "score": 62, "tags": ["warm"], "job_title": "CTO"},
    {"first_name": "Carol", "last_name": "Williams", "email": "carol@initech.com", "company": "Initech", "score": 45, "tags": ["cold"], "job_title": "Marketing Director"},
    {"first_name": "David", "last_name": "Brown", "email": "david@umbrella.com", "company": "Umbrella Corp", "score": 92, "tags": ["vip", "hot"], "job_title": "VP Sales"},
    {"first_name": "Eve", "last_name": "Davis", "email": "eve@stark.com", "company": "Stark Industries", "score": 78, "tags": ["warm", "enterprise"], "job_title": "Head of Marketing"},
    {"first_name": "Frank", "last_name": "Miller", "email": "frank@hooli.com", "company": "Hooli", "score": 34, "tags": ["cold"], "job_title": "Product Manager"},
    {"first_name": "Grace", "last_name": "Wilson", "email": "grace@wayne.com", "company": "Wayne Enterprises", "score": 88, "tags": ["vip"], "job_title": "CMO"},
    {"first_name": "Henry", "last_name": "Taylor", "email": "henry@oscorp.com", "company": "Oscorp", "score": 55, "tags": ["warm"], "job_title": "Sales Director"},
]

SAMPLE_PIPELINES = [
    {
        "name": "Sales Pipeline",
        "description": "Standard B2B sales process",
        "stages": [
            {"name": "Lead", "order": 0, "color": "#6b7280", "probability": 10},
            {"name": "Qualified", "order": 1, "color": "#3b82f6", "probability": 30},
            {"name": "Proposal", "order": 2, "color": "#f59e0b", "probability": 60},
            {"name": "Negotiation", "order": 3, "color": "#f97316", "probability": 80},
            {"name": "Closed Won", "order": 4, "color": "#10b981", "probability": 100},
            {"name": "Closed Lost", "order": 5, "color": "#ef4444", "probability": 0},
        ],
    },
    {
        "name": "Partner Pipeline",
        "description": "Channel partner onboarding & deals",
        "stages": [
            {"name": "Prospecting", "order": 0, "color": "#6b7280", "probability": 10},
            {"name": "Partner Review", "order": 1, "color": "#8b5cf6", "probability": 40},
            {"name": "Contracting", "order": 2, "color": "#f59e0b", "probability": 70},
            {"name": "Partner Active", "order": 3, "color": "#10b981", "probability": 100},
        ],
    },
]

SAMPLE_DEALS = [
    {"name": "Enterprise Platform License", "value": 120000, "contact_idx": 0, "stage_idx": 2, "status": "open"},
    {"name": "Annual SaaS Renewal", "value": 45000, "contact_idx": 2, "stage_idx": 1, "status": "open"},
    {"name": "Consulting Engagement", "value": 28000, "contact_idx": 4, "stage_idx": 0, "status": "open"},
    {"name": "Integration Partnership", "value": 75000, "contact_idx": 6, "stage_idx": 2, "status": "open"},
    {"name": "Quick Win — Starter Pack", "value": 12000, "contact_idx": 1, "stage_idx": 3, "status": "open"},
]


async def seed(session: AsyncSession, *, drop: bool = False) -> None:
    """Run the seed routine."""
    if drop:
        log("🔄 Dropping all data...")
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
        log("✅ All data dropped.\n")

    # 1. Tenant & Workspace
    tenant, _ = await get_or_create(session, Tenant, {"id": TENANT_ID}, defaults={
        "name": "Aegis Demo",
        "slug": "aegis-demo",
        "plan": "enterprise",
        "is_active": True,
    })
    ws, _ = await get_or_create(session, Workspace, {"id": WORKSPACE_ID}, defaults={
        "tenant_id": tenant.id,
        "name": "Main Workspace",
        "slug": "main",
        "is_active": True,
    })

    # 2. Permissions
    perm_map: dict[str, Permission] = {}
    for p in PERMISSIONS:
        perm, _ = await get_or_create(session, Permission, {"code": p["code"]}, defaults={
            "name": p["name"],
            "group": p["group"],
        })
        perm_map[p["code"]] = perm

    # 3. Roles
    for role_name, perm_codes in ROLES.items():
        role, created = await get_or_create(session, Role, {
            "tenant_id": tenant.id,
            "name": role_name,
        }, defaults={
            "description": f"{role_name.capitalize()} role",
            "is_system": True,
        })
        if created:
            for code in perm_codes:
                rp = RolePermission(role_id=role.id, permission_id=perm_map[code].id)
                session.add(rp)
            log(f"  👤 Role '{role_name}' created with {len(perm_codes)} permissions")

    # 4. Admin user
    admin_email = "admin@aegismc.io"
    existing = (await session.execute(select(User).where(User.email == admin_email))).scalar_one_or_none()
    if existing:
        admin = existing
        log(f"  👤 Admin user exists: {admin_email}")
    else:
        admin = User(
            email=admin_email,
            hashed_password=hash_password("admin123"),
            name="Admin User",
            display_name="Admin",
            tenant_id=tenant.id,
            is_active=True,
            is_superuser=True,
        )
        session.add(admin)
        await session.flush()
        log(f"  👤 Admin user created: {admin_email} / admin123")

    # Assign admin role
    admin_role_query = await session.execute(
        select(Role).where(Role.tenant_id == tenant.id, Role.name == "admin")
    )
    admin_role = admin_role_query.scalar_one()
    existing_ur = await session.execute(
        select(UserRole).where(UserRole.user_id == admin.id, UserRole.role_id == admin_role.id)
    )
    if not existing_ur.scalar_one_or_none():
        session.add(UserRole(user_id=admin.id, role_id=admin_role.id, tenant_id=tenant.id))
        log("  → Assigned admin role")

    # 5. Pipelines & Stages
    pipeline_map: dict[str, Pipeline] = {}
    stage_map: dict[str, list[PipelineStage]] = {}
    for pl in SAMPLE_PIPELINES:
        pipeline, created = await get_or_create(session, Pipeline, {
            "workspace_id": ws.id,
            "name": pl["name"],
        }, defaults={
            "description": pl["description"],
            "is_active": True,
        })
        pipeline_map[pl["name"]] = pipeline
        stages = []
        for s in pl["stages"]:
            st, _ = await get_or_create(session, PipelineStage, {
                "pipeline_id": pipeline.id,
                "name": s["name"],
            }, defaults={
                "order": s["order"],
                "color": s["color"],
                "probability": s["probability"],
            })
            stages.append(st)
        stage_map[pl["name"]] = sorted(stages, key=lambda x: x.order or 0)
        if created:
            log(f"  📊 Pipeline '{pl['name']}' created with {len(stages)} stages")

    # 6. Contacts
    contact_objects = []
    for c in SAMPLE_CONTACTS:
        contact, _created = await get_or_create(session, Contact, {
            "workspace_id": ws.id,
            "email": c["email"],
        }, defaults={
            "tenant_id": tenant.id,
            "first_name": c["first_name"],
            "last_name": c["last_name"],
            "company": c.get("company"),
            "score": c.get("score", 0),
            "source": "seed",
            "tags": c.get("tags", []),
            "job_title": c.get("job_title"),
            "is_active": True,
        })
        contact_objects.append(contact)
    log(f"  📇 {len(contact_objects)} contacts seeded")

    # 7. Deals
    primary_pipeline = pipeline_map["Sales Pipeline"]
    pipeline_stages = stage_map["Sales Pipeline"]
    for d in SAMPLE_DEALS:
        stage = pipeline_stages[d["stage_idx"]]
        _deal, created = await get_or_create(session, Deal, {
            "workspace_id": ws.id,
            "name": d["name"],
        }, defaults={
            "tenant_id": tenant.id,
            "value": d["value"],
            "pipeline_id": primary_pipeline.id,
            "pipeline_stage_id": stage.id,
            "contact_id": contact_objects[d["contact_idx"]].id,
            "owner_id": admin.id,
            "status": d["status"],
            "is_active": True,
        })
        if created:
            log(f"  💰 Deal '{d['name']}' (${d['value']:,}) created")
    log(f"  💰 {len(SAMPLE_DEALS)} deals seeded")

    # 8. Sample activities
    activity_types = ["call", "email", "meeting", "note", "task"]
    for i, contact in enumerate(contact_objects[:4]):
        act_type = activity_types[i % len(activity_types)]
        existing_act = await session.execute(
            select(Activity).where(Activity.contact_id == contact.id, Activity.type == act_type)
        )
        if not existing_act.scalar_one_or_none():
            activity = Activity(
                tenant_id=tenant.id,
                workspace_id=ws.id,
                type=act_type,
                subject=f"{act_type.capitalize()} with {contact.first_name} {contact.last_name}",
                description=f"Initial outreach to {contact.email}",
                contact_id=contact.id,
                created_by_id=admin.id,
                is_active=True,
            )
            session.add(activity)
    log("  📋 Sample activities seeded")

    await session.commit()
    log("\n✅ Seed complete!")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed Aegis development database")
    parser.add_argument("--drop", action="store_true", help="Drop all data before seeding")
    args = parser.parse_args()

    if not settings.database_url:
        log("❌ DATABASE_URL is not configured.")
        sys.exit(1)

    log("🌱 Seeding database...")
    log(f"   Database: {settings.database_url}")

    async with async_session_factory() as session:
        await seed(session, drop=args.drop)


if __name__ == "__main__":
    asyncio.run(main())
