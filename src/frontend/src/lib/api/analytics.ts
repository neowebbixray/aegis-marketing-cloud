// ─── Analytics API ─────────────────────────────────────────
// Backend routes: /api/v1/analytics/...

import { apiClient } from '@/lib/api';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ─── Types ─────────────────────────────────────────────────

export type AnalyticsMetric =
  | 'page_views'
  | 'unique_visitors'
  | 'sessions'
  | 'bounce_rate'
  | 'conversion_rate'
  | 'click_through_rate'
  | 'open_rate'
  | 'reply_rate'
  | 'revenue'
  | 'leads_generated'
  | 'deals_won'
  | 'campaign_roi'
  | 'email_deliverability'
  | 'social_engagement'
  | 'search_impressions';

export type AnalyticsGranularity = 'hour' | 'day' | 'week' | 'month' | 'quarter';

export type DashboardType = 'main' | 'marketing' | 'sales' | 'email' | 'custom';

export interface AnalyticsEvent {
  id: string;
  workspace_id: string;
  event_name: string;
  properties: Record<string, unknown>;
  session_id?: string;
  user_id?: string;
  contact_id?: string;
  page_url?: string;
  referrer?: string;
  user_agent?: string;
  ip_address?: string;
  timestamp: string;
}

export interface AnalyticsEventRequest {
  event_name: string;
  properties?: Record<string, unknown>;
  session_id?: string;
  user_id?: string;
  contact_id?: string;
  page_url?: string;
  referrer?: string;
}

export interface MetricValue {
  metric: AnalyticsMetric;
  value: number;
  previous_value?: number;
  change_percentage?: number;
  unit: string;
}

export interface MetricTimeSeries {
  metric: AnalyticsMetric;
  data: Array<{
    timestamp: string;
    value: number;
  }>;
  unit: string;
}

export interface Dashboard {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  type: DashboardType;
  widgets: DashboardWidget[];
  layout: Record<string, unknown>;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface DashboardWidget {
  id: string;
  dashboard_id: string;
  title: string;
  type: 'metric' | 'chart' | 'table' | 'funnel' | 'map';
  metric?: AnalyticsMetric;
  chart_type?: 'line' | 'bar' | 'pie' | 'area' | 'scatter';
  size: 'sm' | 'md' | 'lg' | 'full';
  position: { x: number; y: number };
  config: Record<string, unknown>;
}

export interface Report {
  id: string;
  workspace_id: string;
  name: string;
  description?: string;
  type: string;
  config: Record<string, unknown>;
  schedule?: {
    frequency: 'daily' | 'weekly' | 'monthly';
    recipients: string[];
    last_sent_at?: string;
  };
  last_generated_at?: string;
  created_at: string;
  updated_at: string;
}

export interface CreateDashboardRequest {
  name: string;
  description?: string;
  type: DashboardType;
  widgets?: Omit<DashboardWidget, 'id' | 'dashboard_id'>[];
}

export interface CreateReportRequest {
  name: string;
  description?: string;
  type: string;
  config: Record<string, unknown>;
  schedule?: {
    frequency: 'daily' | 'weekly' | 'monthly';
    recipients: string[];
  };
}

// ─── Analytics API Client ──────────────────────────────────

export const analyticsApi = {
  // ── Events ──

  /** Track an event */
  trackEvent: (data: AnalyticsEventRequest) =>
    apiClient.post<void>('/api/v1/analytics/events', data),

  /** Track multiple events (batch) */
  trackEvents: (events: AnalyticsEventRequest[]) =>
    apiClient.post<void>('/api/v1/analytics/events/batch', { events }),

  /** List events (with filtering) */
  listEvents: (params?: {
    page?: number;
    limit?: number;
    event_name?: string;
    session_id?: string;
    contact_id?: string;
    start_date?: string;
    end_date?: string;
  }) =>
    apiClient
      .get<{ items: AnalyticsEvent[]; total: number; page: number; page_size: number }>(
        '/api/v1/analytics/events',
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
      })) as Promise<PaginatedResponse<AnalyticsEvent>>,

  // ── Metrics ──

  /** Get current metric values */
  getMetrics: (metrics: AnalyticsMetric[], params?: {
    start_date?: string;
    end_date?: string;
    granularity?: AnalyticsGranularity;
  }) =>
    apiClient
      .post<MetricValue[]>('/api/v1/analytics/metrics', { metrics, ...params })
      .then((items) => ({ data: items }) as unknown as ApiResponse<MetricValue[]>),

  /** Get time series for a metric */
  getMetricTimeSeries: (metric: AnalyticsMetric, params: {
    start_date: string;
    end_date: string;
    granularity?: AnalyticsGranularity;
    filters?: Record<string, string>;
  }) =>
    apiClient
      .get<MetricTimeSeries>(`/api/v1/analytics/metrics/${metric}/time-series`, {
        ...params,
        filters: params.filters ? JSON.stringify(params.filters) : undefined,
      } as Record<string, string | number | boolean | undefined>)
      .then((data) => ({ data }) as ApiResponse<MetricTimeSeries>),

  /** Compare metrics across periods */
  compareMetrics: (metrics: AnalyticsMetric[], params: {
    current_start: string;
    current_end: string;
    previous_start: string;
    previous_end: string;
    granularity?: AnalyticsGranularity;
  }) =>
    apiClient
      .post<MetricValue[]>('/api/v1/analytics/metrics/compare', {
        metrics,
        ...params,
      })
      .then((items) => ({ data: items }) as unknown as ApiResponse<MetricValue[]>),

  // ── Dashboards ──

  /** List dashboards */
  listDashboards: () =>
    apiClient.get<Dashboard[]>('/api/v1/analytics/dashboards').then(
      (items) => ({ data: items }) as unknown as ApiResponse<Dashboard[]>
    ),

  /** Get dashboard by ID */
  getDashboard: (id: string) =>
    apiClient.get<Dashboard>(`/api/v1/analytics/dashboards/${id}`).then(
      (data) => ({ data }) as ApiResponse<Dashboard>
    ),

  /** Create a new dashboard */
  createDashboard: (data: CreateDashboardRequest) =>
    apiClient.post<Dashboard>('/api/v1/analytics/dashboards', data).then(
      (data) => ({ data }) as ApiResponse<Dashboard>
    ),

  /** Update dashboard */
  updateDashboard: (id: string, data: Partial<CreateDashboardRequest>) =>
    apiClient.patch<Dashboard>(`/api/v1/analytics/dashboards/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<Dashboard>
    ),

  /** Delete dashboard */
  deleteDashboard: (id: string) =>
    apiClient.delete<void>(`/api/v1/analytics/dashboards/${id}`),

  /** Get dashboard data (rendered widgets) */
  getDashboardData: (id: string, params?: {
    start_date?: string;
    end_date?: string;
    granularity?: AnalyticsGranularity;
  }) =>
    apiClient.get<Record<string, unknown>>(
      `/api/v1/analytics/dashboards/${id}/data`,
      params as Record<string, string | number | boolean | undefined>
    ).then((data) => ({ data }) as ApiResponse<Record<string, unknown>>),

  // ── Reports ──

  /** List reports */
  listReports: (params?: { page?: number; limit?: number; type?: string }) =>
    apiClient
      .get<{ items: Report[]; total: number; page: number; page_size: number }>(
        '/api/v1/analytics/reports',
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
      })) as Promise<PaginatedResponse<Report>>,

  /** Get report by ID */
  getReport: (id: string) =>
    apiClient.get<Report>(`/api/v1/analytics/reports/${id}`).then(
      (data) => ({ data }) as ApiResponse<Report>
    ),

  /** Create a new report */
  createReport: (data: CreateReportRequest) =>
    apiClient.post<Report>('/api/v1/analytics/reports', data).then(
      (data) => ({ data }) as ApiResponse<Report>
    ),

  /** Update report */
  updateReport: (id: string, data: Partial<CreateReportRequest>) =>
    apiClient.patch<Report>(`/api/v1/analytics/reports/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<Report>
    ),

  /** Delete report */
  deleteReport: (id: string) =>
    apiClient.delete<void>(`/api/v1/analytics/reports/${id}`),

  /** Generate report immediately */
  generateReport: (id: string) =>
    apiClient.post<{ report_url: string; generated_at: string }>(
      `/api/v1/analytics/reports/${id}/generate`
    ).then((data) => ({ data }) as ApiResponse<{ report_url: string; generated_at: string }>),

  /** Export analytics data */
  exportData: (params: {
    format: 'csv' | 'xlsx' | 'pdf';
    metrics?: AnalyticsMetric[];
    start_date?: string;
    end_date?: string;
    granularity?: AnalyticsGranularity;
  }) =>
    apiClient.get<Blob>('/api/v1/analytics/export', {
      ...params,
    } as Record<string, string | number | boolean | string[] | undefined>),
};
