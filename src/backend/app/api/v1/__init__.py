"""
API v1 router collection.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    ai,
    admin,
    analytics,
    auth,
    billing,
    crm,
    email,
    health,
    knowledge,
    knowledge_base,
    marketplace,
    media,
    notifications,
    search,
    seo,
    social,
    tenants,
    webhooks,
    ws,
    gdpr,
)

router = APIRouter(prefix="/api/v1")
router.include_router(ai.router)
router.include_router(admin.router)
router.include_router(auth.router)
router.include_router(tenants.router)
router.include_router(billing.router)
router.include_router(crm.router)
router.include_router(seo.router)
router.include_router(social.router)
router.include_router(analytics.router)
router.include_router(knowledge.router)
router.include_router(knowledge_base.router)
router.include_router(notifications.router)
router.include_router(marketplace.router)
router.include_router(media.router)
router.include_router(webhooks.router)
router.include_router(email.router)
router.include_router(health.router)
router.include_router(ws.router)
router.include_router(search.router)
router.include_router(gdpr.router)
