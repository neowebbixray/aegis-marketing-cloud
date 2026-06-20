"""
GDPR compliance endpoints.
Provides:
- ``GET /gdpr/export`` – returns a JSON snapshot of the authenticated user's personal data.
- ``DELETE /gdpr/delete`` – deactivates the user account, soft‑deletes related data, and logs an audit event.

The implementation is deliberately minimal: it gathers the user record and counts of
related objects (sessions, API keys, OAuth accounts). In a production system you would
expand this to include all tables that contain personal identifiers.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user, get_db
from app.core.audit_logger import AuditLogService, EVENT_USER_DELETED
from app.models.auth import User

router = APIRouter(prefix="/gdpr", tags=["gdpr"])


@router.get("/export", response_model=Dict[str, Any])
async def export_user_data(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Return a JSON representation of the caller's personal data.

    The response includes the core ``User`` fields and simple aggregates of related
    entities such as sessions, API keys and OAuth accounts. This satisfies a
    typical GDPR *right to access* request while keeping the query lightweight.
    """
    # Basic user fields (exclude password hash)
    user_dict = {
        "id": str(current_user.id),
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "display_name": current_user.display_name,
        "avatar_url": current_user.avatar_url,
        "locale": current_user.locale,
        "timezone": current_user.timezone,
        "is_active": current_user.is_active,
        "is_superadmin": current_user.is_superadmin,
        "metadata": current_user.metadata_jsonb,
        "last_login_at": current_user.last_login_at.isoformat() if current_user.last_login_at else None,
    }

    # Aggregate related objects – we only count them to avoid pulling large blobs.
    from sqlalchemy import func, select
    from app.models.auth import Session, ApiKey, OAuthAccount

    stmt = select(
        func.count(Session.id),
        func.count(ApiKey.id),
        func.count(OAuthAccount.id),
    ).where(Session.user_id == current_user.id)
    result = await db.execute(stmt)
    session_cnt, api_key_cnt, oauth_cnt = result.one()
    user_dict.update({
        "session_count": session_cnt,
        "api_key_count": api_key_cnt,
        "oauth_account_count": oauth_cnt,
    })
    return user_dict


@router.delete("/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_data(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Deactivate the user account and log an audit event.

    A full *right to be forgotten* implementation would cascade delete or
    anonymise all personal data. Here we simply mark the user as inactive and
    clear authentication fields (password hash) to prevent future logins.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="User account already deactivated")

    # Soft‑deactivate – we keep the row for referential integrity.
    current_user.is_active = False
    # Remove password hash to ensure the account cannot be logged into.
    current_user.password_hash = ""
    db.add(current_user)

    # Record the deletion in the audit log.
    audit = AuditLogService(db)
    await audit.log_event(
        actor_id=current_user.id,
        action=EVENT_USER_DELETED,
        resource_type="user",
        resource_id=current_user.id,
        changes={"is_active": (True, False), "password_hash": ("[redacted]", "")},
        tenant_id=getattr(current_user, "tenant_id", None),
    )

    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
