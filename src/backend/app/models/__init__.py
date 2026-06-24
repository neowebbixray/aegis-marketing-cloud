"""Export all SQLAlchemy models for Alembic and application imports."""

from app.models.ai import AIAgent, AIAgentExecution, Conversation, KnowledgeDocument, Message
from app.models.analytics import AnalyticsEvent, Dashboard, MetricSnapshot, ScheduledReport
from app.models.auth import ApiKey, MfaDevice, OAuthAccount, Session, User
from app.models.base import BaseModel, SoftDeleteMixin, TenantMixin, TimestampMixin
from app.models.billing import CreditWallet, Invoice, Subscription, UsageRecord
from app.models.crm import (
    Activity,
    Contact,
    CustomFieldDefinition,
    Deal,
    LeadScoreHistory,
    Pipeline,
    PipelineStage,
)
from app.models.email import EmailCampaign, EmailMessage
from app.models.marketing import Campaign, EmailTemplate, Funnel, LandingPage, Segment, Tag
from app.models.marketplace import MarketplaceInstallation
from app.models.media import Asset
from app.models.notifications import Notification
from app.models.seo import SeoKeyword
from app.models.social import SocialPost
from app.models.tenant import (
    PendingInvitation,
    Permission,
    Role,
    RolePermission,
    Team,
    TeamMember,
    Tenant,
    UserRole,
    Workspace,
)
from app.models.webhooks import Webhook, WebhookDelivery

__all__ = [
    # AI
    "AIAgent",
    "AIAgentExecution",
    "Activity",
    # Analytics
    "AnalyticsEvent",
    "ApiKey",
    # Media
    "Asset",
    # Base
    "BaseModel",
    # Marketing
    "Campaign",
    # CRM
    "Contact",
    "Conversation",
    "CreditWallet",
    "CustomFieldDefinition",
    "Dashboard",
    "Deal",
    # Email
    "EmailCampaign",
    "EmailMessage",
    "EmailTemplate",
    "Funnel",
    "Invoice",
    "KnowledgeDocument",
    "LandingPage",
    "LeadScoreHistory",
    # Marketplace
    "MarketplaceInstallation",
    "Message",
    "MetricSnapshot",
    "MfaDevice",
    # Notifications
    "Notification",
    "OAuthAccount",
    "PendingInvitation",
    "Permission",
    "Pipeline",
    "PipelineStage",
    "Role",
    "RolePermission",
    "ScheduledReport",
    "Segment",
    # SEO
    "SeoKeyword",
    "Session",
    # Social
    "SocialPost",
    "SoftDeleteMixin",
    # Billing
    "Subscription",
    "Tag",
    "Team",
    "TeamMember",
    # Tenant
    "Tenant",
    "TenantMixin",
    "TimestampMixin",
    "UsageRecord",
    # Auth
    "User",
    "UserRole",
    # Webhooks
    "Webhook",
    "WebhookDelivery",
    "Workspace",
]
