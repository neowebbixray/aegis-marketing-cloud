// ─── Core API Types ───────────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  meta?: PaginationMeta;
  links?: PaginationLinks;
}

export interface PaginatedResponse<T> {
  data: T[];
  meta: PaginationMeta;
  links: PaginationLinks;
}

export interface PaginationMeta {
  page: number;
  per_page: number;
  total: number;
  has_more: boolean;
  cursor?: string;
  offset?: number;
}

export interface PaginationLinks {
  self: string;
  next?: string;
  prev?: string;
}

export interface ApiError {
  type: string;
  title: string;
  status: number;
  detail: string;
  instance: string;
  trace_id?: string;
  errors?: ApiFieldError[];
}

export interface ApiFieldError {
  field: string;
  message: string;
  code: string;
}

// ─── Auth Types ───────────────────────────────────────────

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  confirm_password: string;
  display_name: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  avatar_url?: string;
  roles: string[];
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ─── Tenant / Workspace Types ────────────────────────────

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan: 'free' | 'pro' | 'business' | 'enterprise';
  is_active: boolean;
  created_at: string;
}

export interface Workspace {
  id: string;
  tenant_id: string;
  name: string;
  slug: string;
  description?: string;
  is_default: boolean;
  created_at: string;
}

// ─── CRM Types ────────────────────────────────────────────

export type LifecycleStage =
  | 'lead'
  | 'qualified'
  | 'opportunity'
  | 'customer'
  | 'churned'
  | 'inactive';

export type ContactSource =
  | 'manual'
  | 'import'
  | 'website'
  | 'referral'
  | 'social'
  | 'email'
  | 'api'
  | 'other';

export interface Contact {
  id: string;
  workspace_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  company?: string;
  job_title?: string;
  avatar_url?: string;
  lifecycle_stage: LifecycleStage;
  source: ContactSource;
  owner_id?: string;
  owner?: User;
  tags: string[];
  notes?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateContactRequest {
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  company?: string;
  job_title?: string;
  lifecycle_stage?: LifecycleStage;
  source?: ContactSource;
  owner_id?: string;
  tags?: string[];
  notes?: string;
}

export interface UpdateContactRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  company?: string;
  job_title?: string;
  lifecycle_stage?: LifecycleStage;
  source?: ContactSource;
  owner_id?: string;
  tags?: string[];
  notes?: string;
}

export type DealStage =
  | 'lead_in'
  | 'qualified'
  | 'proposal'
  | 'negotiation'
  | 'closed_won'
  | 'closed_lost';

export interface Deal {
  id: string;
  workspace_id: string;
  name: string;
  value: number;
  currency: string;
  probability: number;
  stage: DealStage;
  pipeline_id: string;
  pipeline_stage_id: string;
  contact_id?: string;
  contact?: Contact;
  owner_id?: string;
  owner?: User;
  expected_close_date?: string;
  notes?: string;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface CreateDealRequest {
  name: string;
  value: number;
  currency?: string;
  probability?: number;
  stage?: DealStage;
  pipeline_id: string;
  pipeline_stage_id: string;
  contact_id?: string;
  owner_id?: string;
  expected_close_date?: string;
  notes?: string;
  tags?: string[];
}

export interface UpdateDealRequest {
  name?: string;
  value?: number;
  currency?: string;
  probability?: number;
  stage?: DealStage;
  pipeline_id?: string;
  pipeline_stage_id?: string;
  contact_id?: string;
  owner_id?: string;
  expected_close_date?: string;
  notes?: string;
  tags?: string[];
}

export interface Pipeline {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  is_default: boolean;
  stages: PipelineStage[];
  created_at: string;
  updated_at: string;
}

export interface PipelineStage {
  id: string;
  pipeline_id: string;
  name: string;
  color: string;
  order: number;
  probability: number;
  created_at: string;
}

export interface CreatePipelineRequest {
  name: string;
  description?: string;
  stages: { name: string; color: string; probability: number }[];
}

// ─── Notification Types ─────────────────────────────────────

export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  read: boolean;
  workspace_id?: string;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export type ActivityType =
  | 'note'
  | 'call'
  | 'email'
  | 'meeting'
  | 'task'
  | 'deal_update'
  | 'stage_change'
  | 'system';

export interface Activity {
  id: string;
  workspace_id: string;
  contact_id?: string;
  deal_id?: string;
  type: ActivityType;
  title: string;
  description?: string;
  metadata?: Record<string, unknown>;
  created_by: string;
  created_at: string;
}
