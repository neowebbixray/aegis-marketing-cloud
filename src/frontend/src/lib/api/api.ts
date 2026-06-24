// ─── CRM API ───────────────────────────────────────────────
// Backend routes: /api/v1/crm/...
//
// Exports: contactsApi, dealsApi, pipelinesApi, activitiesApi,
//          customFieldsApi.

import { apiClient } from '@/lib/api';
import type {
  ApiResponse,
  PaginatedResponse,
  Contact,
  CreateContactRequest,
  UpdateContactRequest,
  Activity,
  Deal,
  CreateDealRequest,
  UpdateDealRequest,
  Pipeline,
  CreatePipelineRequest,
  CustomFieldDefinition,
  CreateCustomFieldDefinitionRequest,
  UpdateCustomFieldDefinitionRequest,
} from '@/types';

export type {
  Contact,
  CreateContactRequest,
  UpdateContactRequest,
  Activity,
  Deal,
  CreateDealRequest,
  UpdateDealRequest,
  Pipeline,
  CreatePipelineRequest,
  CustomFieldDefinition,
  CreateCustomFieldDefinitionRequest,
  UpdateCustomFieldDefinitionRequest,
};

// ─── Custom Field Definitions ─────────────────────────────

export const customFieldsApi = {
  list: (params?: Record<string, string | number | boolean | undefined>) =>
    apiClient
      .get<{ items: CustomFieldDefinition[]; total: number; page: number; page_size: number }>(
        '/api/v1/custom-fields',
        params
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: res.page,
          per_page: res.page_size,
          total: res.total,
          has_more: res.page * res.page_size < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<CustomFieldDefinition>>,

  get: (id: string) =>
    apiClient.get<CustomFieldDefinition>(`/api/v1/custom-fields/${id}`).then(
      (data) => ({ data }) as ApiResponse<CustomFieldDefinition>
    ),

  create: (data: CreateCustomFieldDefinitionRequest) =>
    apiClient.post<CustomFieldDefinition>('/api/v1/custom-fields', data).then(
      (data) => ({ data }) as ApiResponse<CustomFieldDefinition>
    ),

  update: (id: string, data: UpdateCustomFieldDefinitionRequest) =>
    apiClient.patch<CustomFieldDefinition>(`/api/v1/custom-fields/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<CustomFieldDefinition>
    ),

  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/custom-fields/${id}`),

  /** Reorder custom field definitions */
  reorder: (fieldIds: string[]) =>
    apiClient.put<void>('/api/v1/custom-fields/reorder', { field_ids: fieldIds }),
};

// ─── Contacts ─────────────────────────────────────────────

export const contactsApi = {
  list: (params?: Record<string, string | number | boolean | undefined>) =>
    apiClient
      .get<{ items: Contact[]; total: number; page: number; page_size: number }>(
        '/api/v1/crm/contacts',
        params
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: res.page,
          per_page: res.page_size,
          total: res.total,
          has_more: res.page * res.page_size < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<Contact>>,

  get: (id: string) =>
    apiClient.get<Contact>(`/api/v1/crm/contacts/${id}`).then(
      (data) => ({ data }) as ApiResponse<Contact>
    ),

  /** Get activities for a contact */
  getActivities: (id: string) =>
    apiClient
      .get<{ items: Activity[]; total: number; page: number; page_size: number }>(
        `/api/v1/crm/contacts/${id}/activities`
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: res.page,
          per_page: res.page_size,
          total: res.total,
          has_more: res.page * res.page_size < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<Activity>>,

  create: (data: CreateContactRequest) =>
    apiClient.post<Contact>('/api/v1/crm/contacts', data).then(
      (data) => ({ data }) as ApiResponse<Contact>
    ),

  update: (id: string, data: UpdateContactRequest) =>
    apiClient.patch<Contact>(`/api/v1/crm/contacts/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<Contact>
    ),

  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/contacts/${id}`),

  /** Full-text search across contacts */
  search: (query: string, params?: { limit?: number; offset?: number }) =>
    apiClient
      .get<{ items: Contact[]; total: number; offset: number }>(
        '/api/v1/crm/contacts/search',
        { q: query, ...params } as Record<string, string | number | boolean | undefined>
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: params?.offset ? Math.floor(params.offset / (params?.limit || 10)) + 1 : 1,
          per_page: params?.limit || 10,
          total: res.total,
          has_more: res.offset + (params?.limit || 10) < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<Contact>>,

  /** Update lead score for a contact */
  updateLeadScore: (id: string, score: number, score_source: string, scoring_factors?: Record<string, unknown>) =>
    apiClient
      .post<Contact>(`/api/v1/crm/contacts/${id}/lead-score`, {
        score,
        score_source,
        scoring_factors,
      })
      .then((data) => ({ data }) as ApiResponse<Contact>),
};

// ─── Deals ────────────────────────────────────────────────

export const dealsApi = {
  list: (params?: Record<string, string | number | boolean | undefined>) =>
    apiClient
      .get<{ items: Deal[]; total: number; page: number; page_size: number }>(
        '/api/v1/crm/deals',
        params
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: res.page,
          per_page: res.page_size,
          total: res.total,
          has_more: res.page * res.page_size < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<Deal>>,

  get: (id: string) =>
    apiClient.get<Deal>(`/api/v1/crm/deals/${id}`).then(
      (data) => ({ data }) as ApiResponse<Deal>
    ),

  create: (data: CreateDealRequest) =>
    apiClient.post<Deal>('/api/v1/crm/deals', data).then(
      (data) => ({ data }) as ApiResponse<Deal>
    ),

  update: (id: string, data: UpdateDealRequest) =>
    apiClient.patch<Deal>(`/api/v1/crm/deals/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<Deal>
    ),

  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/deals/${id}`),

  /** Move a deal to a different pipeline stage.
   *
   * Corresponds to ``PATCH /api/v1/crm/deals/{id}/stage``.
   * The ``won_reason`` / ``lost_reason`` fields are passed through
   * to ``DealStageChangeRequest`` so winning/losing can be recorded
   * in the same call when the target stage is a closing stage.
   */
  moveStage: (
    id: string,
    new_stage_id: string,
    reason?: string,
    won_reason?: string,
    lost_reason?: string
  ) =>
    apiClient
      .patch<Deal>(`/api/v1/crm/deals/${id}/stage`, {
        pipeline_stage_id: new_stage_id,
        reason,
        won_reason,
        lost_reason,
      } as Record<string, string | undefined>)
      .then((data) => ({ data }) as ApiResponse<Deal>),

  /** Mark a deal as won (updates won_reason via ``PATCH /api/v1/crm/deals/{id}``). */
  markWon: (id: string, won_reason?: string) =>
    apiClient
      .patch<Deal>(`/api/v1/crm/deals/${id}`, { won_reason } as Record<string, string | undefined>)
      .then((data) => ({ data }) as ApiResponse<Deal>),

  /** Mark a deal as lost (updates lost_reason via ``PATCH /api/v1/crm/deals/{id}``). */
  markLost: (id: string, lost_reason?: string) =>
    apiClient
      .patch<Deal>(`/api/v1/crm/deals/${id}`, { lost_reason } as Record<string, string | undefined>)
      .then((data) => ({ data }) as ApiResponse<Deal>),
};

// ─── Pipelines ────────────────────────────────────────────

export const pipelinesApi = {
  /** List all pipelines for the current workspace */
  list: () =>
    apiClient
      .get<{ items: Pipeline[]; total: number; page: number; page_size: number }>(
        '/api/v1/crm/pipelines'
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: res.page,
          per_page: res.page_size,
          total: res.total,
          has_more: res.page * res.page_size < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<Pipeline>>,

  /** Get a single pipeline with its stages eagerly loaded */
  get: (id: string) =>
    apiClient.get<Pipeline>(`/api/v1/crm/pipelines/${id}`).then(
      (data) => ({ data }) as ApiResponse<Pipeline>
    ),

  /** Create a pipeline with optional stages */
  create: (data: CreatePipelineRequest) =>
    apiClient.post<Pipeline>('/api/v1/crm/pipelines', data).then(
      (data) => ({ data }) as ApiResponse<Pipeline>
    ),

  /** Update pipeline metadata */
  update: (id: string, data: Partial<CreatePipelineRequest>) =>
    apiClient.patch<Pipeline>(`/api/v1/crm/pipelines/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<Pipeline>
    ),

  /** Delete a pipeline */
  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/pipelines/${id}`),

  /** Reorder pipeline stages */
  reorderStages: (pipelineId: string, stageIds: string[]) =>
    apiClient
      .put<void>(`/api/v1/crm/pipelines/${pipelineId}/stages/reorder`, {
        stage_ids: stageIds,
      })
      .then((data) => ({ data }))
    };

// ─── Activities ───────────────────────────────────────────

export const activitiesApi = {
  /** List activities with optional filters */
  list: (params?: Record<string, string | number | boolean | undefined>) =>
    apiClient
      .get<{ items: Activity[]; total: number; page: number; page_size: number }>(
        '/api/v1/crm/activities',
        params
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: res.page,
          per_page: res.page_size,
          total: res.total,
          has_more: res.page * res.page_size < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<Activity>>,

  /** Get a single activity */
  get: (id: string) =>
    apiClient.get<Activity>(`/api/v1/crm/activities/${id}`).then(
      (data) => ({ data }) as ApiResponse<Activity>
    ),

  /** Log a new activity */
  create: (data: { workspace_id: string; type: string; subject: string; description?: string; contact_id?: string; deal_id?: string; user_id?: string }) =>
    apiClient.post<Activity>('/api/v1/crm/activities', data).then(
      (data) => ({ data }) as ApiResponse<Activity>
    ),

  /** Update an activity */
  update: (id: string, data: Partial<{ type: string; subject: string; description?: string }>) =>
    apiClient.patch<Activity>(`/api/v1/crm/activities/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<Activity>
    ),

  /** Delete an activity */
  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/activities/${id}`),
};
