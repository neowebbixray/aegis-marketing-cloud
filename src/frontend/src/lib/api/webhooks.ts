// ─── Webhooks API ──────────────────────────────────────────
// Backend routes: /api/v1/webhooks/...

import { apiClient } from '@/lib/api';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ─── Types ─────────────────────────────────────────────────

export type WebhookEvent =
  | 'contact.created'
  | 'contact.updated'
  | 'contact.deleted'
  | 'deal.created'
  | 'deal.updated'
  | 'deal.deleted'
  | 'pipeline.stage.changed'
  | 'invoice.paid'
  | 'invoice.overdue'
  | 'subscription.updated'
  | 'subscription.canceled'
  | 'campaign.sent'
  | 'campaign.completed'
  | 'form.submitted'
  | 'media.uploaded'
  | 'ai.generation.completed'
  | '*';

export type WebhookStatus = 'active' | 'inactive' | 'disabled';

export type WebhookDeliveryStatus = 'success' | 'failed' | 'retrying' | 'pending';

export interface Webhook {
  id: string;
  workspace_id: string;
  name: string;
  url: string;
  description?: string;
  events: WebhookEvent[];
  secret: string;
  status: WebhookStatus;
  retry_count: number;
  timeout_seconds: number;
  headers?: Record<string, string>;
  filter_expression?: string;
  last_success_at?: string;
  last_failure_at?: string;
  consecutive_failures: number;
  created_at: string;
  updated_at: string;
}

export interface CreateWebhookRequest {
  name: string;
  url: string;
  events: WebhookEvent[];
  description?: string;
  retry_count?: number;
  timeout_seconds?: number;
  headers?: Record<string, string>;
  filter_expression?: string;
}

export interface UpdateWebhookRequest {
  name?: string;
  url?: string;
  events?: WebhookEvent[];
  description?: string;
  status?: WebhookStatus;
  retry_count?: number;
  timeout_seconds?: number;
  headers?: Record<string, string>;
  filter_expression?: string;
}

export interface WebhookDelivery {
  id: string;
  webhook_id: string;
  event_type: string;
  status: WebhookDeliveryStatus;
  request_url: string;
  request_headers: Record<string, string>;
  request_body: string;
  response_status?: number;
  response_body?: string;
  response_headers?: Record<string, string>;
  duration_ms?: number;
  attempt_number: number;
  next_retry_at?: string;
  error_message?: string;
  completed_at?: string;
  created_at: string;
}

export interface WebhookTestResult {
  success: boolean;
  status_code?: number;
  response_body?: string;
  duration_ms: number;
  error?: string;
}

export interface WebhookSecretRotateResponse {
  secret: string;
  previous_secret: string;
  rotated_at: string;
}

// ─── Webhooks API Client ───────────────────────────────────

export const webhooksApi = {
  // ── CRUD ──

  /** List webhooks */
  list: (params?: { page?: number; limit?: number; status?: WebhookStatus }) =>
    apiClient
      .get<{ items: Webhook[]; total: number; page: number; page_size: number }>(
        '/api/v1/webhooks',
        params as Record<string, string | number | boolean | undefined>
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
      })) as Promise<PaginatedResponse<Webhook>>,

  /** Get webhook by ID */
  get: (id: string) =>
    apiClient.get<Webhook>(`/api/v1/webhooks/${id}`).then(
      (data) => ({ data }) as ApiResponse<Webhook>
    ),

  /** Create a new webhook */
  create: (data: CreateWebhookRequest) =>
    apiClient.post<Webhook>('/api/v1/webhooks', data).then(
      (data) => ({ data }) as ApiResponse<Webhook>
    ),

  /** Update a webhook */
  update: (id: string, data: UpdateWebhookRequest) =>
    apiClient.patch<Webhook>(`/api/v1/webhooks/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<Webhook>
    ),

  /** Delete a webhook */
  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/webhooks/${id}`),

  /** Toggle webhook active/inactive */
  toggle: (id: string, active: boolean) =>
    apiClient.patch<Webhook>(`/api/v1/webhooks/${id}`, {
      status: active ? 'active' : 'inactive',
    }).then((data) => ({ data }) as ApiResponse<Webhook>),

  // ── Delivery Logs ──

  /** List delivery logs for a webhook */
  listDeliveries: (webhookId: string, params?: {
    page?: number;
    limit?: number;
    status?: WebhookDeliveryStatus;
  }) =>
    apiClient
      .get<{ items: WebhookDelivery[]; total: number; page: number; page_size: number }>(
        `/api/v1/webhooks/${webhookId}/deliveries`,
        params as Record<string, string | number | boolean | undefined>
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
      })) as Promise<PaginatedResponse<WebhookDelivery>>,

  /** Get a single delivery log */
  getDelivery: (webhookId: string, deliveryId: string) =>
    apiClient.get<WebhookDelivery>(
      `/api/v1/webhooks/${webhookId}/deliveries/${deliveryId}`
    ).then((data) => ({ data }) as ApiResponse<WebhookDelivery>),

  /** Retry a failed delivery */
  retryDelivery: (webhookId: string, deliveryId: string) =>
    apiClient.post<WebhookDelivery>(
      `/api/v1/webhooks/${webhookId}/deliveries/${deliveryId}/retry`
    ).then((data) => ({ data }) as ApiResponse<WebhookDelivery>),

  // ── Test ──

  /** Test a webhook by sending a sample event */
  test: (id: string, event?: WebhookEvent) =>
    apiClient.post<WebhookTestResult>(
      `/api/v1/webhooks/${id}/test`,
      event ? { event } : undefined
    ).then((data) => ({ data }) as ApiResponse<WebhookTestResult>),

  // ── Secret Rotation ──

  /** Rotate webhook secret */
  rotateSecret: (id: string) =>
    apiClient.post<WebhookSecretRotateResponse>(
      `/api/v1/webhooks/${id}/rotate-secret`
    ).then((data) => ({ data }) as ApiResponse<WebhookSecretRotateResponse>),
};
