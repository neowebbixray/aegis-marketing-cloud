"""
Admin router: feature flags, system management, and tenant overrides.

Requires superadmin privileges for most endpoints.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_user
from app.core.feature_flags import (
    FEATURE_FLAG_DEFINITIONS,
    FeatureFlag,
    feature_flag_service,
)
from app.models.auth import User
from app.schemas.base import build_single_response
from app.schemas.feature_flags import (
    FeatureFlagDefinitionResponse,
    FeatureFlagOverrideResponse,
    FeatureFlagToggleRequest,
    FeatureFlagsListResponse,
    SetFeatureFlagOverrideRequest,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_superadmin(user: User) -> None:
    """Ensure the current user is a superadmin."""
    if not user.is_superadmin:
        from app.core.exceptions import ForbiddenException

        raise ForbiddenException(detail="Superadmin privileges required")


@router.get(
    "/feature-flags",
    response_model=FeatureFlagsListResponse,
    summary="List all feature flag definitions and overrides",
)
async def list_feature_flags(
    current_user: User = Depends(get_current_active_user),
) -> FeatureFlagsListResponse:
    """Return all feature flag definitions with current state and overrides.

    Requires superadmin privileges.
    """
    _require_superadmin(current_user)

    definitions = feature_flag_service.get_feature_definitions()
    overrides = feature_flag_service.get_all_overrides()

    flags = []
    for flag, definition in definitions.items():
        flags.append(
            FeatureFlagDefinitionResponse(
                feature=flag.value,
                description=definition.description,
                default_enabled_tiers=sorted(definition.default_enabled_tiers),
                beta=definition.beta,
                internal=definition.internal,
            )
        )

    override_list = []
    for tenant_id, tenant_overrides in overrides.items():
        for flag_val, enabled in tenant_overrides.items():
            override_list.append(
                FeatureFlagOverrideResponse(
                    tenant_id=tenant_id,
                    feature=flag_val.value if hasattr(flag_val, "value") else str(flag_val),
                    enabled=enabled,
                )
            )

    return FeatureFlagsListResponse(
        flags=flags,
        overrides=override_list,
    )


@router.patch(
    "/feature-flags/{tenant_id}",
    response_model=FeatureFlagOverrideResponse,
    summary="Set a feature flag override for a tenant",
)
async def set_feature_flag_override(
    tenant_id: str,
    body: SetFeatureFlagOverrideRequest,
    current_user: User = Depends(get_current_active_user),
) -> FeatureFlagOverrideResponse:
    """Set (or clear) a feature flag override for a specific tenant.

    Requires superadmin privileges.
    """
    _require_superadmin(current_user)

    # Validate feature flag exists
    try:
        flag = FeatureFlag(body.feature)
    except ValueError:
        from app.core.exceptions import NotFoundException

        raise NotFoundException(detail=f"Unknown feature flag: {body.feature}")

    if body.enabled is True:
        feature_flag_service.set_override(tenant_id, flag, True)
    elif body.enabled is False:
        feature_flag_service.set_override(tenant_id, flag, False)
    else:
        # None → clear override
        feature_flag_service.clear_override(tenant_id, flag)

    current_enabled = feature_flag_service.is_enabled(
        flag, tenant_id=tenant_id
    )

    return FeatureFlagOverrideResponse(
        tenant_id=tenant_id,
        feature=flag.value,
        enabled=current_enabled,
    )
