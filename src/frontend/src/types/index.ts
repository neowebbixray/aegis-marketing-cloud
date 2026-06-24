// ─── API Response Wrappers ─────────────────────────────────

export interface ApiResponse<T> {
  data: T;
  meta?: {
    page: number;
    per_page: number;
    total: number;
    has_more: boolean;
  };
  links?: { self: string | null };
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {}

// ─── CRM Types ─────────────────────────────────────────────

export interface User {
  id: string;
  email: string;
  name: string;
  display_name?: string;
  avatar_url?: string | null;
  roles?: string[];
  is_active?: boolean;
}

export interface DealStage {
  id: string;
  pipeline_id: string;
  name: string;
  order: number;
  probability?: number | null;
  colour?: string | null;
}

export type PipelineStage = DealStage;

export interface Contact {
  id: string;
  tenant_id: string;
  workspace_id?: string;
  first_name: string;
  last_name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
  position?: string | null;
  avatar_url?: string | null;
  lifecycle_stage: string;
  source?: string | null;
  custom_fields: Record<string, unknown>;
  tags: string[];
  owner_id?: string | null;
  owner?: User | null;
  notes?: string;
  score?: number | null;
  score_updated_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateContactRequest {
  workspace_id?: string;
  first_name: string;
  last_name: string;
  email?: string;
  phone?: string;
  company?: string;
  position?: string;
  lifecycle_stage?: string;
  source?: string;
  custom_fields?: Record<string, unknown>;
  tags?: string[];
  owner_id?: string;
}

export interface UpdateContactRequest {
  first_name?: string;
  last_name?: string;
  email?: string;
  phone?: string;
  company?: string;
  position?: string;
  lifecycle_stage?: string;
  source?: string;
  custom_fields?: Record<string, unknown>;
  tags?: string[];
  owner_id?: string;
}

export interface Deal {
  id: string;
  workspace_id?: string;
  name: string;
  value?: number | null;
  currency: string;
  probability?: number | null;
  stage: string;
  pipeline_id: string;
  pipeline_stage_id: string;
  contact_id?: string | null;
  contact?: Contact | null;
  owner_id?: string | null;
  owner?: User | null;
  expected_close_date?: string | null;
  custom_fields: Record<string, unknown>;
  tags: string[];
  notes?: string;
  // Win/Loss tracking fields
  lost_reason?: string | null;
  lost_at?: string | null;
  won_reason?: string | null;
  won_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateDealRequest {
  workspace_id?: string;
  name: string;
  value?: number;
  currency?: string;
  probability?: number;
  pipeline_stage_id: string;
  contact_id?: string;
  organization_label?: string;
  owner_id?: string;
  expected_close_date?: string;
  custom_fields?: Record<string, unknown>;
}

export interface UpdateDealRequest {
  name?: string;
  value?: number;
  currency?: string;
  probability?: number;
  pipeline_stage_id?: string;
  contact_id?: string;
  owner_id?: string;
  expected_close_date?: string;
  custom_fields?: Record<string, unknown>;
}

export interface Pipeline {
  id: string;
  workspace_id?: string;
  name: string;
  description?: string | null;
  is_default: boolean;
  stages: DealStage[];
  created_at: string;
  updated_at: string;
}

export interface CreatePipelineRequest {
  workspace_id?: string;
  name: string;
  description?: string;
  is_default?: boolean;
  stages?: {
    name: string;
    order?: number;
    probability?: number;
    colour?: string;
  }[];
}

export interface Activity {
  id: string;
  workspace_id?: string;
  type: ActivityType;
  subject: string;
  description?: string | null;
  contact_id?: string | null;
  deal_id?: string | null;
  user_id?: string | null;
  created_at: string;
  updated_at: string;
}

export type ActivityType = 'note' | 'call' | 'email' | 'meeting' | 'task';

export type LifecycleStage = 'lead' | 'qualified' | 'opportunity' | 'customer' | 'churned' | 'inactive';

export type ContactSource = 'manual' | 'import' | 'website' | 'referral' | 'social' | 'email' | 'api' | 'other';

export type CustomFieldType =
  | 'text'
  | 'number'
  | 'date'
  | 'dropdown'
  | 'multi_select'
  | 'url';

export interface CustomFieldDefinition {
  id: string;
  workspace_id?: string;
  name: string;
  key: string;
  description?: string;
  field_type: CustomFieldType;
  config: Record<string, unknown>;
  is_required: boolean;
  is_active: boolean;
  display_order: number;
  created_at: string;
  updated_at: string;
}

export interface CreateCustomFieldDefinitionRequest {
  workspace_id?: string;
  name: string;
  key: string;
  description?: string;
  field_type: CustomFieldType;
  config?: Record<string, unknown>;
  is_required?: boolean;
  is_active?: boolean;
  display_order?: number;
}

export interface UpdateCustomFieldDefinitionRequest {
  name?: string;
  key?: string;
  description?: string;
  field_type?: CustomFieldType;
  config?: Record<string, unknown>;
  is_required?: boolean;
  is_active?: boolean;
  display_order?: number;
}

// ─── Notification Types ────────────────────────────────────

export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message?: string;
  read: boolean;
  created_at?: string;
}

// ─── Auth Types ────────────────────────────────────────────

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type?: string;
  expires_in?: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  confirm_password?: string;
  display_name?: string;
}

// ─── Workspace Types ───────────────────────────────────────

export interface Workspace {
  id: string;
  name: string;
  is_default: boolean;
}
