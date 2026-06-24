"""Export all service classes for convenience imports."""

from app.services.ai_service import AIService
from app.services.analytics import (
    AnalyticsService,
    CampaignAnalyticsService,
    DashboardService,
    FunnelAnalyticsService,
    ReportService,
)
from app.services.auth import AuthService
from app.services.billing import BillingService
from app.services.crm import (
    ActivityService,
    ContactService,
    CustomFieldDefinitionService,
    DealService,
    PipelineService,
)
from app.services.email_service import EmailService
from app.services.knowledge_base import ArticleService, CategoryService
from app.services.knowledge_base import SearchService as KnowledgeBaseSearchService
from app.services.knowledge_service import KnowledgeService, QdrantManager
from app.services.marketing import (
    CampaignService,
    EmailTemplateService,
    FunnelService,
    LandingPageService,
    SegmentService,
)
from app.services.marketplace import InstallationService, ListingService, ReviewService
from app.services.media import MediaService
from app.services.notifications import (
    DigestService,
    NotificationPreferencesService,
    NotificationService,
)
from app.services.search_service import SearchService
from app.services.seo import BacklinkService, KeywordService, SiteAuditService
from app.services.social import SocialAnalyticsService, SocialListeningService, SocialPostService
from app.services.tenant import TenantService
from app.services.webhooks import WebhookService
from app.services.workflows import N8nClient

__all__ = [
    "AIService",
    "ActivityService",
    "AnalyticsService",
    "ArticleService",
    "AuthService",
    "BacklinkService",
    "BillingService",
    "CampaignAnalyticsService",
    "CampaignService",
    "CategoryService",
    "ContactService",
    "CustomFieldDefinitionService",
    "DashboardService",
    "DealService",
    "DigestService",
    "EmailService",
    "EmailTemplateService",
    "FunnelAnalyticsService",
    "FunnelService",
    "InstallationService",
    "KeywordService",
    "KnowledgeBaseSearchService",
    "KnowledgeService",
    "LandingPageService",
    "ListingService",
    "MediaService",
    "N8nClient",
    "NotificationPreferencesService",
    "NotificationService",
    "PipelineService",
    "QdrantManager",
    "ReportService",
    "ReviewService",
    "SearchService",
    "SegmentService",
    "SiteAuditService",
    "SocialAnalyticsService",
    "SocialListeningService",
    "SocialPostService",
    "TenantService",
    "WebhookService",
]
