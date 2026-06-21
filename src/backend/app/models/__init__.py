"""
Export all SQLAlchemy models for Alembic and application imports.
"""
from app.models.ai import AIAgent, AIAgentExecution, Conversation, KnowledgeDocument, Message
from app.models.analytics import AnalyticsEvent, Dashboard, MetricSnapshot, ScheduledReport
from app.models.auth import ApiKey, MfaDevice, OAuthAccount, Session, User
from app.models.base import BaseModel, SoftDeleteMixin, TenantMixin, TimestampMixin
from app.models.billing import CreditWallet, Invoice, Subscription, UsageRecord
from app.models.crm import Activity, Contact, CustomFieldDefinition, Deal, LeadScoreHistory, Pipeline, PipelineStage
from app.models.email import EmailCampaign, EmailMessage
from app.models.marketing import Campaign, EmailTemplate, Funnel, LandingPage, Segment, Tag
from app.models.marketplace import MarketplaceInstallation
from app.models.media import Asset
from app.models.notifications import Notification
from app.models.seo import SeoKeyword
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
    "CustomFieldDefinition",
    "Deal",
    "LeadScoreHistory",
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