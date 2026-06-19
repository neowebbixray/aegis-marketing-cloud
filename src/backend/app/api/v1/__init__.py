"""
API v1 router collection.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import analytics, auth, crm, knowledge_base, marketplace, notifications, seo, social, tenants

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(tenants.router)
router.include_router(crm.router)
router.include_router(seo.router)
router.include_router(social.router)
router.include_router(analytics.router)
router.include_router(knowledge_base.router)
router.include_router(notifications.router)
router.include_router(marketplace.router)
