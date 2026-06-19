"""
Pydantic schemas for feature flag management endpoints.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FeatureFlagDefinitionResponse(BaseModel):
    """A single feature flag definition."""

    feature: str = Field(..., description="Feature flag identifier")
    description: str = Field(..., description="Human-readable description")
    default_enabled_tiers: list[str] = Field(
        ..., description="Tiers where this flag is enabled by default"
    )
    beta: bool = False
    internal: bool = False


class FeatureFlagOverrideResponse(BaseModel):
    """A single feature flag override for a tenant."""

    tenant_id: str = Field(..., description="Tenant ID")
    feature: str = Field(..., description="Feature flag identifier")
    enabled: bool = Field(..., description="Current effective value")


class FeatureFlagsListResponse(BaseModel):
    """Response for listing all feature flags."""

    flags: list[FeatureFlagDefinitionResponse]
    overrides: list[FeatureFlagOverrideResponse]


class SetFeatureFlagOverrideRequest(BaseModel):
    """Request to set a feature flag override for a tenant."""

    feature: str = Field(..., description="Feature flag identifier")
    enabled: bool | None = Field(
        ...,
        description="True=enable, False=disable, None=clear override",
    )


class FeatureFlagToggleRequest(BaseModel):
    """Request to toggle a single feature flag for evaluation."""

    feature: str = Field(..., description="Feature flag identifier")
    tenant_tier: str = Field("free", description="Tenant pricing tier")
    tenant_id: str | None = Field(None, description="Optional tenant ID for overrides")
