"""
Feature flags for Aegis Marketing Cloud.

Defines:
- FeatureFlag enum with all application features
- FeatureFlagService with tier-based evaluation
- In-memory cache with per-tenant override capability
- Admin API helpers
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from app.config import settings

# ── Feature Flag Enum ────────────────────────────────────────────────────────


class FeatureFlag(str, Enum):
    """All feature flags in the application."""

    AI_AGENTS = "ai_agents"
    ADVANCED_ANALYTICS = "advanced_analytics"
    SSO_AUTH = "sso_auth"
    WEBHOOKS = "webhooks"
    MEDIA_LIBRARY = "media_library"
    BILLING = "billing"
    MARKETPLACE = "marketplace"
    WORKFLOW_AUTOMATION = "workflow_automation"
    WHITE_LABEL = "white_label"
    AUDIT_LOG = "audit_log"
    CUSTOM_ROLES = "custom_roles"
    API_ACCESS = "api_access"
    EXPORT_CSV = "export_csv"
    BRANDING = "branding"
    EMAIL_CAMPAIGNS = "email_campaigns"
    LANDING_PAGES = "landing_pages"
    CRM = "crm"
    SEO_TOOLS = "seo_tools"
    SOCIAL_MEDIA = "social_media"
    MULTI_WORKSPACE = "multi_workspace"


# ── Tier definitions ─────────────────────────────────────────────────────────

TierName = str  # "free" | "starter" | "professional" | "enterprise"


@dataclass
class FlagDefinition:
    """Definition of a single feature flag with tier rules."""

    feature: FeatureFlag
    default_enabled_tiers: set[TierName] = field(default_factory=set)
    description: str = ""
    beta: bool = False
    internal: bool = False
    depends_on: list[FeatureFlag] = field(default_factory=list)


# Tier hierarchy (higher index = more permissive)
TIER_HIERARCHY: dict[TierName, int] = {
    "free": 0,
    "starter": 1,
    "professional": 2,
    "enterprise": 3,
}

# ── Feature flag registry ────────────────────────────────────────────────────

FEATURE_FLAG_DEFINITIONS: dict[FeatureFlag, FlagDefinition] = {
    FeatureFlag.AI_AGENTS: FlagDefinition(
        feature=FeatureFlag.AI_AGENTS,
        default_enabled_tiers={"professional", "enterprise"},
        description="AI-powered marketing agents",
    ),
    FeatureFlag.ADVANCED_ANALYTICS: FlagDefinition(
        feature=FeatureFlag.ADVANCED_ANALYTICS,
        default_enabled_tiers={"professional", "enterprise"},
        description="Advanced analytics and reporting",
    ),
    FeatureFlag.SSO_AUTH: FlagDefinition(
        feature=FeatureFlag.SSO_AUTH,
        default_enabled_tiers={"enterprise"},
        description="SSO/SAML enterprise authentication",
    ),
    FeatureFlag.WEBHOOKS: FlagDefinition(
        feature=FeatureFlag.WEBHOOKS,
        default_enabled_tiers={"starter", "professional", "enterprise"},
        description="Outgoing webhook integrations",
    ),
    FeatureFlag.MEDIA_LIBRARY: FlagDefinition(
        feature=FeatureFlag.MEDIA_LIBRARY,
        default_enabled_tiers={"starter", "professional", "enterprise"},
        description="Media library and asset management",
    ),
    FeatureFlag.BILLING: FlagDefinition(
        feature=FeatureFlag.BILLING,
        default_enabled_tiers={"professional", "enterprise"},
        description="Billing and invoicing",
    ),
    FeatureFlag.MARKETPLACE: FlagDefinition(
        feature=FeatureFlag.MARKETPLACE,
        default_enabled_tiers={"enterprise"},
        description="Marketplace for extensions and integrations",
    ),
    FeatureFlag.WORKFLOW_AUTOMATION: FlagDefinition(
        feature=FeatureFlag.WORKFLOW_AUTOMATION,
        default_enabled_tiers={"professional", "enterprise"},
        description="Workflow automation tools",
    ),
    FeatureFlag.WHITE_LABEL: FlagDefinition(
        feature=FeatureFlag.WHITE_LABEL,
        default_enabled_tiers={"enterprise"},
        description="White-label branding",
    ),
    FeatureFlag.AUDIT_LOG: FlagDefinition(
        feature=FeatureFlag.AUDIT_LOG,
        default_enabled_tiers={"professional", "enterprise"},
        description="Audit log for compliance",
    ),
    FeatureFlag.CUSTOM_ROLES: FlagDefinition(
        feature=FeatureFlag.CUSTOM_ROLES,
        default_enabled_tiers={"enterprise"},
        description="Custom RBAC roles",
    ),
    FeatureFlag.API_ACCESS: FlagDefinition(
        feature=FeatureFlag.API_ACCESS,
        default_enabled_tiers={"starter", "professional", "enterprise"},
        description="Programmatic API access",
    ),
    FeatureFlag.EXPORT_CSV: FlagDefinition(
        feature=FeatureFlag.EXPORT_CSV,
        default_enabled_tiers={"free", "starter", "professional", "enterprise"},
        description="Export data to CSV",
    ),
    FeatureFlag.BRANDING: FlagDefinition(
        feature=FeatureFlag.BRANDING,
        default_enabled_tiers={"starter", "professional", "enterprise"},
        description="Custom branding",
    ),
    FeatureFlag.EMAIL_CAMPAIGNS: FlagDefinition(
        feature=FeatureFlag.EMAIL_CAMPAIGNS,
        default_enabled_tiers={"starter", "professional", "enterprise"},
        description="Email campaign management",
    ),
    FeatureFlag.LANDING_PAGES: FlagDefinition(
        feature=FeatureFlag.LANDING_PAGES,
        default_enabled_tiers={"starter", "professional", "enterprise"},
        description="Landing page builder",
    ),
    FeatureFlag.CRM: FlagDefinition(
        feature=FeatureFlag.CRM,
        default_enabled_tiers={"starter", "professional", "enterprise"},
        description="CRM functionality",
    ),
    FeatureFlag.SEO_TOOLS: FlagDefinition(
        feature=FeatureFlag.SEO_TOOLS,
        default_enabled_tiers={"professional", "enterprise"},
        description="SEO tools and analysis",
    ),
    FeatureFlag.SOCIAL_MEDIA: FlagDefinition(
        feature=FeatureFlag.SOCIAL_MEDIA,
        default_enabled_tiers={"starter", "professional", "enterprise"},
        description="Social media management",
    ),
    FeatureFlag.MULTI_WORKSPACE: FlagDefinition(
        feature=FeatureFlag.MULTI_WORKSPACE,
        default_enabled_tiers={"enterprise"},
        description="Multiple workspaces per tenant",
    ),
}


# ── Feature Flag Service ─────────────────────────────────────────────────────


class FeatureFlagService:
    """Service for evaluating feature flags.

    Maintains an in-memory cache of per-tenant overrides. In production this
    would be backed by Redis or the database.
    """

    def __init__(self) -> None:
        self._tenant_overrides: dict[str, dict[FeatureFlag, bool]] = {}

    # ── Public API ────────────────────────────────────────────────────────

    def is_enabled(
        self,
        feature: FeatureFlag,
        tenant_tier: TierName = "free",
        tenant_id: str | None = None,
    ) -> bool:
        """Check whether *feature* is enabled for the given tenant.

        Resolution order:
        1. Per-tenant override (if set via admin API)
        2. Flag definition's tier rules
        3. ``False`` (feature not found)
        """
        # Check overrides
        if tenant_id and tenant_id in self._tenant_overrides:
            override = self._tenant_overrides[tenant_id].get(feature)
            if override is not None:
                return override

        # Check tier rules
        definition = FEATURE_FLAG_DEFINITIONS.get(feature)
        if definition is None:
            return False

        return tenant_tier in definition.default_enabled_tiers

    def set_override(
        self, tenant_id: str, feature: FeatureFlag, enabled: bool
    ) -> None:
        """Set a per-tenant override for a feature flag."""
        if tenant_id not in self._tenant_overrides:
            self._tenant_overrides[tenant_id] = {}
        self._tenant_overrides[tenant_id][feature] = enabled

    def clear_override(self, tenant_id: str, feature: FeatureFlag) -> None:
        """Remove a per-tenant override for a feature flag."""
        overrides = self._tenant_overrides.get(tenant_id)
        if overrides:
            overrides.pop(feature, None)

    def clear_all_overrides(self, tenant_id: str | None = None) -> None:
        """Clear overrides for a tenant, or all tenants if not specified."""
        if tenant_id:
            self._tenant_overrides.pop(tenant_id, None)
        else:
            self._tenant_overrides.clear()

    def get_all_overrides(self) -> dict[str, dict[FeatureFlag, bool]]:
        """Return all current overrides (for admin display)."""
        return dict(self._tenant_overrides)

    def get_feature_definitions(self) -> dict[FeatureFlag, FlagDefinition]:
        """Return all feature flag definitions."""
        return dict(FEATURE_FLAG_DEFINITIONS)


# ── Global singleton ─────────────────────────────────────────────────────────

feature_flag_service = FeatureFlagService()
