// ─── Workflows API ──────────────────────────────────────────
// Backend routes: /api/v1/workflows/...

import { apiClient } from '@/lib/api';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ─── Types ─────────────────────────────────────────────────

export interface WorkflowTrigger {
  type: string;
  config: Record<string, unknown>;
}

export interface WorkflowStep {
  id: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  order: number;
  next_step_id?: string | null;
}

export interface Workflow {
  id: string;
  workspaceId: string;
  name: string;
  description?: string | null;
  active: boolean;
  trigger: WorkflowTrigger;
  steps: WorkflowStep[];
  nodes?: WorkflowStep[];
  connections?: Record<string, unknown>;
  versionId?: string;
  createdAt: string;
  updatedAt: string;
  lastTriggeredAt?: string | null;
}

export interface CreateWorkflowRequest {
  name: string;
  description?: string;
  trigger: WorkflowTrigger;
  steps: Omit<WorkflowStep, 'id'>[];
}

export interface UpdateWorkflowRequest {
  name?: string;
  description?: string;
  is_active?: boolean;
  trigger?: WorkflowTrigger;
  steps?: Omit<WorkflowStep, 'id'>[];
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  mode?: string;
  input: Record<string, unknown>;
  output?: Record<string, unknown> | null;
  error?: string | null;
  startedAt?: string | null;
  completedAt?: string | null;
  stoppedAt?: string | null;
  created_at: string;
}

// ─── Workflows API Client ───────────────────────────────────

export const workflowsApi = {
  /** List workflows */
  list: (params?: { limit?: number; offset?: number; status?: string }) =>
    apiClient
      .get<{ items: Workflow[]; total: number; page: number; page_size: number }>(
        '/api/v1/workflows/',
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
      })) as Promise<PaginatedResponse<Workflow>>,

  /** Get workflow by ID */
  get: (id: string) =>
    apiClient.get<Workflow>(`/api/v1/workflows/${id}`).then(
      (data) => ({ data }) as ApiResponse<Workflow>
    ),

  /** Create a new workflow */
  create: (data: CreateWorkflowRequest) =>
    apiClient.post<Workflow>('/api/v1/workflows/', data).then(
      (data) => ({ data }) as ApiResponse<Workflow>
    ),

  /** Update a workflow */
  update: (id: string, data: UpdateWorkflowRequest) =>
    apiClient.patch<Workflow>(`/api/v1/workflows/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<Workflow>
    ),

  /** Delete a workflow */
  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/workflows/${id}`),

  /** Trigger a workflow manually */
  trigger: (id: string, payload: Record<string, unknown> = {}) =>
    apiClient
      .post<{ execution_id: string; status: string }>(`/api/v1/workflows/${id}/trigger`, payload)
      .then((data) => ({ data }) as ApiResponse<{ execution_id: string; status: string }>),

  /** Get executions for a workflow */
  getExecutions: (
    id: string,
    params?: { limit?: number; offset?: number; status?: string }
  ) =>
    apiClient
      .get<{ items: WorkflowExecution[]; total: number; page: number; page_size: number }>(
        `/api/v1/workflows/${id}/executions`,
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
      })) as Promise<PaginatedResponse<WorkflowExecution>>,

  /** Get a specific execution */
  getExecution: (workflowId: string, executionId: string) =>
    apiClient
      .get<WorkflowExecution>(`/api/v1/workflows/${workflowId}/executions/${executionId}`)
      .then((data) => ({ data }) as ApiResponse<WorkflowExecution>),
};