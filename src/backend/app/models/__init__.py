"""Export all SQLAlchemy models for Alembic and application imports."""
from app.models.base import BaseModel, TimestampMixin, SoftDeleteMixin, TenantMixin
from app.models.auth import User, OAuthAccount, Session, MfaDevice, ApiKey
from app.models.tenant import (
    Tenant,
    Workspace,
    Team,
    TeamMember,
    Role,
    Permission,
    RolePermission,
    UserRole,
    PendingInvitation,
)
from app.models.crm import Contact, Deal, Pipeline, PipelineStage, Activity
from app.models.marketing import Campaign, EmailTemplate, LandingPage, Funnel, Segment, Tag
from app.models.ai import AIAgent, AIAgentExecution, KnowledgeDocument, Conversation, Message
from app.models.billing import Subscription, Invoice, CreditWallet, UsageRecord
from app.models.media import Asset
from app.models.webhooks import Webhook, WebhookDelivery
from app.models.analytics import AnalyticsEvent, Dashboard, MetricSnapshot, ScheduledReport
from app.models.email import EmailCampaign, EmailMessage
from app.models.marketplace import MarketplaceInstallation
from app.models.notifications import Notification
from app.models.seo import SeoKeyword

__all__ = [
    # Base
    "BaseModel",
    "TimestampMixin",
    "SoftDeleteMixin",
    "TenantMixin",
    # Auth
    "User",
    "OAuthAccount",
    "Session",
    "MfaDevice",
    "ApiKey",
    # Tenant
    "Tenant",
    "Workspace",
    "Team",
    "TeamMember",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",
    "PendingInvitation",
    # CRM
    "Contact",
    "Deal",
    "Pipeline",
    "PipelineStage",
    "Activity",
    # Marketing
    "Campaign",
    "EmailTemplate",
    "LandingPage",
    "Funnel",
    "Segment",
    "Tag",
    # AI
    "AIAgent",
    "AIAgentExecution",
    "KnowledgeDocument",
    "Conversation",
    "Message",
    # Billing
    "Subscription",
    "Invoice",
    "CreditWallet",
    "UsageRecord",
    # Media
    "Asset",
    # Webhooks
    "Webhook",
    "WebhookDelivery",
    # Analytics
    "AnalyticsEvent",
    "MetricSnapshot",
    "Dashboard",
    "ScheduledReport",
    # Marketplace
    "MarketplaceInstallation",
    # Notifications
    "Notification",
    # SEO
    "SeoKeyword",
    # Social
    "SocialPost",
    # Email
    "EmailCampaign",
    "EmailMessage",
]
