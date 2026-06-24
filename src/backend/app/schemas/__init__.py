"""Pydantic schemas for all API domains."""

# ── Base ──
# ── AI ──
from app.schemas.ai import (
    AgentDefinition,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentListResponse,
    ClassificationRequest,
    ClassificationResponse,
    ContentAnalyzeRequest,
    ContentAnalyzeResponse,
    ContentGenerateRequest,
    ContentGenerateResponse,
    ConversationCreate,
    ConversationDetailResponse,
    ConversationResponse,
    ExecutionHistoryResponse,
    GenerateReportRequest,
    GenerateReportResponse,
    LeadScoreRequest,
    LeadScoreResponse,
    MessageCreate,
    MessageResponse,
    SummarizeRequest,
    SummarizeResponse,
    TranslationRequest,
    TranslationResponse,
)

# ── Analytics ──
from app.schemas.analytics import (
    CampaignAnalyticsResponse,
    DashboardCreate,
    DashboardResponse,
    DashboardUpdate,
    EventCreate,
    EventListResponse,
    EventResponse,
    FunnelAnalyticsResponse,
    MetricDataPoint,
    MetricDefinition,
    MetricQuery,
    ReportCreate,
    ReportGenerateResponse,
    ReportResponse,
    ReportUpdate,
    ScheduleReportRequest,
    WidgetConfig,
)

# ── Auth ──
from app.schemas.auth import (
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ChangePasswordRequest,
    CreateApiKeyRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateMeRequest,
    UserResponse,
)
from app.schemas.base import (
    ErrorDetail,
    ErrorEnvelope,
    FieldError,
    ListEnvelope,
    PaginationLinks,
    PaginationMeta,
    SingleEnvelope,
)

# ── Billing ──
from app.schemas.billing import (
    InvoiceResponse,
    PaymentHistoryResponse,
    SubscriptionCancel,
    SubscriptionCreate,
    SubscriptionResponse,
    SubscriptionUpdate,
    UsageRecordResponse,
    UsageSummaryResponse,
    WalletResponse,
    WalletTopUp,
)

# ── CRM ──
from app.schemas.crm import (
    ActivityCreate,
    ActivityResponse,
    ActivityTypeCreate,
    ActivityTypeResponse,
    ActivityTypeUpdate,
    ActivityUpdate,
    ContactCreate,
    ContactResponse,
    ContactUpdate,
    CustomFieldDefinitionCreate,
    CustomFieldDefinitionResponse,
    CustomFieldDefinitionUpdate,
    DealCreate,
    DealResponse,
    DealStageChangeRequest,
    DealUpdate,
    LeadScoreHistoryResponse,
    LeadScoreUpdate,
    PipelineCreate,
    PipelineResponse,
)

# ── Email ──
from app.schemas.email import (
    BounceWebhookPayload,
    CampaignResponse,
    DeliveryResponse,
    EmailAddress,
    EmailTemplateCreate,
    EmailTemplateResponse,
    EmailTemplateUpdate,
    SendBulkItem,
    SendBulkRequest,
    SendBulkResponse,
    SendRequest,
    SendResponse,
    TrackingResponse,
)

# ── Feature Flags ──
from app.schemas.feature_flags import (
    FeatureFlagDefinitionResponse,
    FeatureFlagOverrideResponse,
    FeatureFlagsListResponse,
    FeatureFlagToggleRequest,
    SetFeatureFlagOverrideRequest,
)

# ── Knowledge ──
from app.schemas.knowledge import (
    CollectionStatsResponse,
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    DocumentUploadResponse,
    ReindexResponse,
    SearchQuery,
    SearchResponse,
    SearchResult,
)

# ── Knowledge Base ──
from app.schemas.knowledge_base import (
    ArticleCreate,
    ArticleResponse,
    ArticleUpdate,
    ArticleVersionResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    SearchResultResponse,
)

# ── Marketing ──
from app.schemas.marketing import (
    CampaignCreate,
    CampaignUpdate,
    FunnelCreate,
    FunnelResponse,
    FunnelUpdate,
    LandingPageCreate,
    LandingPageResponse,
    LandingPageUpdate,
    SegmentCreate,
    SegmentResponse,
    SegmentUpdate,
)

# ── Marketplace ──
from app.schemas.marketplace import (
    InstallationResponse,
    ListingDetailResponse,
    ListingResponse,
    ReviewCreate,
    ReviewResponse,
)

# ── Media ──
from app.schemas.media import (
    AssetResponse,
    AssetUpdate,
    AssetUploadMetadata,
    BatchDeleteRequest,
    BatchDeleteResponse,
    DownloadUrlResponse,
    ThumbnailParams,
)

# ── Notifications ──
from app.schemas.notifications import (
    NotificationCreate,
    NotificationListResponse,
    NotificationResponse,
    NotificationType,
    NotificationUpdate,
    WebSocketMessage,
    WebSocketMessageType,
)

# ── Search ──
from app.schemas.search import (
    GlobalSearchResultItem,
    GlobalSearchResults,
    SearchResultItem,
    SearchResults,
)

# ── SEO ──
from app.schemas.seo import (
    BacklinkResponse,
    BacklinkSummaryResponse,
    KeywordCreate,
    KeywordResponse,
    KeywordUpdate,
    RankingHistoryResponse,
    SiteAuditCreate,
    SiteAuditResponse,
)

# ── Social ──
from app.schemas.social import (
    CalendarEntryResponse,
    MentionResponse,
    PostCreate,
    PostResponse,
    PostUpdate,
    SocialAnalyticsResponse,
)

# ── SSO ──
from app.schemas.sso import (
    SAMLLoginResponse,
    SSOCallbackRequest,
    SSOInitiateResponse,
    SSOProviderListResponse,
    SSOProviderResponse,
    SSOTokenResponse,
)

# ── Tenant ──
from app.schemas.tenant import (
    InviteUserRequest,
    RoleResponse,
    TenantResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)

# ── Webhooks ──
from app.schemas.webhooks import (
    DeliveryStatus,
    RetryConfig,
    WebhookCreate,
    WebhookDeliveryResponse,
    WebhookEventCatalogResponse,
    WebhookEventType,
    WebhookResponse,
    WebhookSecretRotateResponse,
    WebhookTestResponse,
    WebhookUpdate,
)

__all__ = [
    # crm
    "ActivityCreate",
    "ActivityResponse",
    "ActivityTypeCreate",
    "ActivityTypeResponse",
    "ActivityTypeUpdate",
    "ActivityUpdate",
    # ai
    "AgentDefinition",
    "AgentExecuteRequest",
    "AgentExecuteResponse",
    "AgentListResponse",
    # auth
    "ApiKeyCreatedResponse",
    "ApiKeyResponse",
    # knowledge_base
    "ArticleCreate",
    "ArticleResponse",
    "ArticleUpdate",
    "ArticleVersionResponse",
    # media
    "AssetResponse",
    "AssetUpdate",
    "AssetUploadMetadata",
    # seo
    "BacklinkResponse",
    "BacklinkSummaryResponse",
    "BatchDeleteRequest",
    "BatchDeleteResponse",
    # email
    "BounceWebhookPayload",
    # social
    "CalendarEntryResponse",
    # analytics
    "CampaignAnalyticsResponse",
    # marketing
    "CampaignCreate",
    "CampaignResponse",
    "CampaignResponse",
    "CampaignUpdate",
    "CategoryCreate",
    "CategoryResponse",
    "CategoryUpdate",
    "ChangePasswordRequest",
    "ClassificationRequest",
    "ClassificationResponse",
    # knowledge
    "CollectionStatsResponse",
    "ContactCreate",
    "ContactResponse",
    "ContactUpdate",
    "ContentAnalyzeRequest",
    "ContentAnalyzeResponse",
    "ContentGenerateRequest",
    "ContentGenerateResponse",
    "ConversationCreate",
    "ConversationDetailResponse",
    "ConversationResponse",
    "CreateApiKeyRequest",
    "CustomFieldDefinitionCreate",
    "CustomFieldDefinitionResponse",
    "CustomFieldDefinitionUpdate",
    "DashboardCreate",
    "DashboardResponse",
    "DashboardUpdate",
    "DealCreate",
    "DealResponse",
    "DealStageChangeRequest",
    "DealUpdate",
    "DeliveryResponse",
    # webhooks
    "DeliveryStatus",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentUpdate",
    "DocumentUploadResponse",
    "DownloadUrlResponse",
    "EmailAddress",
    "EmailTemplateCreate",
    "EmailTemplateCreate",
    "EmailTemplateResponse",
    "EmailTemplateResponse",
    "EmailTemplateUpdate",
    "EmailTemplateUpdate",
    # base
    "ErrorDetail",
    "ErrorEnvelope",
    "EventCreate",
    "EventListResponse",
    "EventResponse",
    "ExecutionHistoryResponse",
    # feature_flags
    "FeatureFlagDefinitionResponse",
    "FeatureFlagOverrideResponse",
    "FeatureFlagToggleRequest",
    "FeatureFlagsListResponse",
    "FieldError",
    "FunnelAnalyticsResponse",
    "FunnelCreate",
    "FunnelResponse",
    "FunnelUpdate",
    "GenerateReportRequest",
    "GenerateReportResponse",
    # search
    "GlobalSearchResultItem",
    "GlobalSearchResults",
    # marketplace
    "InstallationResponse",
    # tenant
    "InviteUserRequest",
    # billing
    "InvoiceResponse",
    "KeywordCreate",
    "KeywordResponse",
    "KeywordUpdate",
    "LandingPageCreate",
    "LandingPageResponse",
    "LandingPageUpdate",
    "LeadScoreHistoryResponse",
    "LeadScoreRequest",
    "LeadScoreResponse",
    "LeadScoreUpdate",
    "ListEnvelope",
    "ListingDetailResponse",
    "ListingResponse",
    "LoginRequest",
    "MentionResponse",
    "MessageCreate",
    "MessageResponse",
    "MetricDataPoint",
    "MetricDefinition",
    "MetricQuery",
    # notifications
    "NotificationCreate",
    "NotificationListResponse",
    "NotificationResponse",
    "NotificationType",
    "NotificationUpdate",
    "PaginationLinks",
    "PaginationMeta",
    "PaymentHistoryResponse",
    "PipelineCreate",
    "PipelineResponse",
    "PostCreate",
    "PostResponse",
    "PostUpdate",
    "RankingHistoryResponse",
    "RefreshRequest",
    "RegisterRequest",
    "ReindexResponse",
    "ReportCreate",
    "ReportGenerateResponse",
    "ReportResponse",
    "ReportUpdate",
    "RetryConfig",
    "ReviewCreate",
    "ReviewResponse",
    "RoleResponse",
    # sso
    "SAMLLoginResponse",
    "SSOCallbackRequest",
    "SSOInitiateResponse",
    "SSOProviderListResponse",
    "SSOProviderResponse",
    "SSOTokenResponse",
    "ScheduleReportRequest",
    "SearchQuery",
    "SearchResponse",
    "SearchResult",
    "SearchResultItem",
    "SearchResultResponse",
    "SearchResults",
    "SegmentCreate",
    "SegmentResponse",
    "SegmentUpdate",
    "SendBulkItem",
    "SendBulkRequest",
    "SendBulkResponse",
    "SendRequest",
    "SendResponse",
    "SetFeatureFlagOverrideRequest",
    "SingleEnvelope",
    "SiteAuditCreate",
    "SiteAuditResponse",
    "SocialAnalyticsResponse",
    "SubscriptionCancel",
    "SubscriptionCreate",
    "SubscriptionResponse",
    "SubscriptionUpdate",
    "SummarizeRequest",
    "SummarizeResponse",
    "TenantResponse",
    "ThumbnailParams",
    "TokenResponse",
    "TrackingResponse",
    "TranslationRequest",
    "TranslationResponse",
    "UpdateMeRequest",
    "UsageRecordResponse",
    "UsageSummaryResponse",
    "UserResponse",
    "WalletResponse",
    "WalletTopUp",
    "WebSocketMessage",
    "WebSocketMessageType",
    "WebhookCreate",
    "WebhookDeliveryResponse",
    "WebhookEventCatalogResponse",
    "WebhookEventType",
    "WebhookResponse",
    "WebhookSecretRotateResponse",
    "WebhookTestResponse",
    "WebhookUpdate",
    "WidgetConfig",
    "WorkspaceCreate",
    "WorkspaceResponse",
    "WorkspaceUpdate",
]
