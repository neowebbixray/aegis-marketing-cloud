import { useAuthStore } from '@/stores/auth-store';
import { useWorkspaceStore } from '@/stores/workspace-store';
import type {
  ApiResponse,
  PaginatedResponse,
  Contact,
  CreateContactRequest,
  UpdateContactRequest,
  Deal,
  CreateDealRequest,
  UpdateDealRequest,
  Pipeline,
  CreatePipelineRequest,
  AuthTokens,
  User,
  LoginRequest,
  RegisterRequest,
  Workspace,
  Activity,
  PaginationMeta,
} from '@/types';

// ─── API Error Class ──────────────────────────────────────

export class ApiError extends Error {
  status: number;
  detail: string;
  errors?: Array<{ field: string; message: string; code: string }>;

  constructor(status: number, detail: string, errors?: Array<{ field: string; message: string; code: string }>) {
    super(detail);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.errors = errors;
  }
}

// ─── Backend Response Shapes ──────────────────────────────
// The backend returns flat objects — not wrapped in {data: T}.
// List endpoints use {items: T[], total, page, page_size}.

interface BackendListResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

function toPaginated<T>(backend: BackendListResponse<T>): PaginatedResponse<T> {
  return {
    data: backend.items,
    meta: {
      page: backend.page,
      per_page: backend.page_size,
      total: backend.total,
      has_more: backend.page * backend.page_size < backend.total,
    },
    links: {
      self: '',
    },
  };
}

function toApiResponse<T>(item: T): ApiResponse<T> {
  return { data: item };
}

// ─── Fetch Wrapper ────────────────────────────────────────

type RequestOptions = {
  method?: string;
  headers?: Record<string, string>;
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
};

const BASE_URL = ''; // Uses Next.js rewrites proxy

async function request<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', headers = {}, body, params } = options;

  // Build URL with query params
  const url = new URL(`${BASE_URL}${endpoint}`, window.location.origin);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.set(key, String(value));
      }
    });
  }

  // Build headers
  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  // Inject auth token
  const token = useAuthStore.getState().token;
  if (token) {
    requestHeaders['Authorization'] = `Bearer ${token}`;
  }

  // Inject workspace header
  const currentWorkspace = useWorkspaceStore.getState().currentWorkspace;
  if (currentWorkspace) {
    requestHeaders['X-Workspace-ID'] = currentWorkspace.id;
  }

  try {
    const response = await fetch(url.toString(), {
      method,
      headers: requestHeaders,
      body: body ? JSON.stringify(body) : undefined,
    });

    // Handle 401 — redirect to login
    if (response.status === 401) {
      useAuthStore.getState().logout();
      if (typeof window !== 'undefined') {
        window.location.href = '/login';
      }
      throw new ApiError(401, 'Authentication required');
    }

    // Handle non-OK responses
    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        throw new ApiError(response.status, response.statusText);
      }

      const apiError = errorData?.error || errorData;
      throw new ApiError(
        response.status,
        apiError?.detail || apiError?.title || response.statusText,
        apiError?.errors
      );
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(0, 'Network error. Please check your connection.');
  }
}

// ─── API Client ───────────────────────────────────────────

export const apiClient = {
  get: <T>(endpoint: string, params?: Record<string, string | number | boolean | undefined>) =>
    request<T>(endpoint, { params }),

  post: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, { method: 'POST', body }),

  put: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, { method: 'PUT', body }),

  patch: <T>(endpoint: string, body?: unknown) =>
    request<T>(endpoint, { method: 'PATCH', body }),

  delete: <T>(endpoint: string) =>
    request<T>(endpoint, { method: 'DELETE' }),
};

// ─── Auth API ─────────────────────────────────────────────
// Backend returns TokenResponse {access_token, refresh_token, token_type, expires_in}
// for register/login/refresh, 204 for logout, UserResponse for /me.

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<AuthTokens>('/api/v1/auth/login', data),

  register: (data: RegisterRequest) =>
    apiClient.post<AuthTokens>('/api/v1/auth/register', data),

  logout: () =>
    apiClient.post<void>('/api/v1/auth/logout'),

  refresh: (refreshToken: string) =>
    apiClient.post<AuthTokens>('/api/v1/auth/refresh', { refresh_token: refreshToken }),

  me: () =>
    apiClient.get<User>('/api/v1/auth/me'),
};

// ─── Tenant / Workspace API ───────────────────────────────
// Backend tenant router is at /api/v1/tenants/workspaces

export const workspaceApi = {
  list: () =>
    apiClient.get<Workspace[]>('/api/v1/tenants/workspaces'),

  get: (id: string) =>
    apiClient.get<Workspace>(`/api/v1/tenants/workspaces/${id}`),
};

export const tenantApi = {
  list: () =>
    apiClient.get('/api/v1/tenants'),

  getCurrent: () =>
    apiClient.get('/api/v1/tenants/current'),
};

// ─── Contacts API ─────────────────────────────────────────
// Backend returns ContactListResponse {items, total, page, page_size} for list/search
// and raw ContactResponse for single items. We transform to PaginatedResponse/ApiResponse.

export const contactsApi = {
  list: (params?: {
    page?: number;
    limit?: number;
    search?: string;
    stage?: string;
    source?: string;
    owner_id?: string;
    sort?: string;
  }) => {
    // Backend uses skip/limit not page/limit
    const skip = params?.page && params?.limit ? (params.page - 1) * params.limit : 0;
    return apiClient
      .get<BackendListResponse<Contact>>('/api/v1/crm/contacts', {
        skip,
        limit: params?.limit ?? 50,
        ...(params?.search ? { search: params.search } : {}),
        ...(params?.stage ? { stage: params.stage } : {}),
        ...(params?.source ? { source: params.source } : {}),
      } as Record<string, string | number | boolean | undefined>)
      .then(toPaginated);
  },

  get: (id: string) =>
    apiClient.get<Contact>(`/api/v1/crm/contacts/${id}`).then(toApiResponse),

  create: (data: CreateContactRequest) =>
    apiClient.post<Contact>('/api/v1/crm/contacts', data).then(toApiResponse),

  update: (id: string, data: UpdateContactRequest) =>
    apiClient.patch<Contact>(`/api/v1/crm/contacts/${id}`, data).then(toApiResponse),

  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/contacts/${id}`),

  search: (query: string, params?: { limit?: number; offset?: number }) =>
    apiClient
      .post<BackendListResponse<Contact>>('/api/v1/crm/contacts/search', {
        ...params,
        query,
      })
      .then(toPaginated),

  getActivities: (id: string) =>
    apiClient.get<Activity[]>(`/api/v1/crm/contacts/${id}/activities`).then(toApiResponse),
};

// ─── Deals API ────────────────────────────────────────────

export const dealsApi = {
  list: (params?: {
    page?: number;
    limit?: number;
    pipeline_id?: string;
    stage?: string;
    search?: string;
    sort?: string;
  }) => {
    const skip = params?.page && params?.limit ? (params.page - 1) * params.limit : 0;
    return apiClient
      .get<BackendListResponse<Deal>>('/api/v1/crm/deals', {
        skip,
        limit: params?.limit ?? 50,
        ...(params?.pipeline_id ? { pipeline_id: params.pipeline_id } : {}),
        ...(params?.stage ? { stage: params.stage } : {}),
      } as Record<string, string | number | boolean | undefined>)
      .then(toPaginated);
  },

  get: (id: string) =>
    apiClient.get<Deal>(`/api/v1/crm/deals/${id}`).then(toApiResponse),

  create: (data: CreateDealRequest) =>
    apiClient.post<Deal>('/api/v1/crm/deals', data).then(toApiResponse),

  update: (id: string, data: UpdateDealRequest) =>
    apiClient.patch<Deal>(`/api/v1/crm/deals/${id}`, data).then(toApiResponse),

  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/deals/${id}`),
};

// ─── Pipelines API ────────────────────────────────────────

export const pipelinesApi = {
  list: () =>
    apiClient.get<Pipeline[]>('/api/v1/crm/pipelines').then(
      (items) => toApiResponse(items) as unknown as { data: Pipeline[] }
    ),

  get: (id: string) =>
    apiClient.get<Pipeline>(`/api/v1/crm/pipelines/${id}`).then(toApiResponse),

  create: (data: CreatePipelineRequest) =>
    apiClient.post<Pipeline>('/api/v1/crm/pipelines', data).then(toApiResponse),

  update: (id: string, data: Partial<CreatePipelineRequest>) =>
    apiClient.patch<Pipeline>(`/api/v1/crm/pipelines/${id}`, data).then(toApiResponse),

  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/pipelines/${id}`),

  reorderStages: (pipelineId: string, stageIds: string[]) =>
    apiClient
      .put<Pipeline>(`/api/v1/crm/pipelines/${pipelineId}/stages/reorder`, { stage_ids: stageIds })
      .then(toApiResponse),
};
