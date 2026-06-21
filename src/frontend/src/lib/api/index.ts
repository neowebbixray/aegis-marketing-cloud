// ─── API Barrel Export ─────────────────────────────────────

export { billingApi } from './billing';
export type {
  SubscriptionPlan,
  Subscription,
  Invoice,
  InvoiceLineItem,
  Wallet,
  WalletTransaction,
  UsageRecord,
  UsageSummary,
  UsageRecordRequest,
  ChangePlanRequest,
  PaymentMethod,
} from './billing';

export { mediaApi } from './media';
export type {
  MediaType,
  MediaStatus,
  MediaAsset,
  MediaUploadRequest,
  MediaUpdateRequest,
  MediaFolder,
  MediaUploadResult,
} from './media';

export { webhooksApi } from './webhooks';
export type {
  WebhookEvent,
  WebhookStatus,
  WebhookDeliveryStatus,
  Webhook,
  CreateWebhookRequest,
  UpdateWebhookRequest,
  WebhookDelivery,
  WebhookTestResult,
  WebhookSecretRotateResponse,
} from './webhooks';

export { analyticsApi } from './analytics';
export type {
  AnalyticsMetric,
  AnalyticsGranularity,
  DashboardType,
  AnalyticsEvent,
  AnalyticsEventRequest,
  MetricValue,
  MetricTimeSeries,
  Dashboard,
  DashboardWidget,
  Report,
  CreateDashboardRequest,
  CreateReportRequest,
} from './analytics';

export { aiApi } from './ai';
export type {
  AgentStatus,
  AgentCapability,
  ConversationStatus,
  ContentType,
  ClassificationTask,
  Agent,
  CreateAgentRequest,
  UpdateAgentRequest,
  Message,
  Conversation,
  CreateConversationRequest,
  SendMessageRequest,
  GenerationRequest,
  GenerationResult,
  ClassificationRequest,
  ClassificationResult,
} from './ai';

export { knowledgeApi } from './knowledge';
export type {
  DocumentStatus,
  DocumentSource,
  IndexingStatus,
  KnowledgeDocument,
  DocumentUploadRequest,
  DocumentUpdateRequest,
  SearchQuery,
  SearchResult,
  IndexingJob,
} from './knowledge';

export {
  customFieldsApi,
  contactsApi,
  dealsApi,
  pipelinesApi,
  activitiesApi,
} from './api';
export type {
  CustomFieldType,
  CustomFieldDefinition,
  CreateCustomFieldDefinitionRequest,
  UpdateCustomFieldDefinitionRequest,
  Contact,
  CreateContactRequest,
  UpdateContactRequest,
  Deal,
  DealStage,
  CreateDealRequest,
  UpdateDealRequest,
  Pipeline,
  CreatePipelineRequest,
  Activity,
} from './api';
