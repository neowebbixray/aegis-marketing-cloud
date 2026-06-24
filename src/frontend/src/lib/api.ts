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
} from '@/types';

// ─── API Error Class ──────────────────────────────────
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

// ─── Backend Response Shapes ──────────────────────────
// The backend returns the envelope: { data, meta, links }
// List endpoints: data = items[], meta = pagination, links = pagination links
// Single endpoints: data = item

interface BackendListResponse<T> {
  data: T[];
  meta: {
    page: number;
    per_page: number;
    total: number;
    has_more: boolean;
  };
  links: {
    self: string | null;
    next: string | null;
    prev: string | null;
  };
}

function toPaginated<T>(backend: BackendListResponse<T>): PaginatedResponse<T> {
  return {
    data: backend.data,
    meta: {
      page: backend.meta.page,
      per_page: backend.meta.per_page,
      total: backend.meta.total,
      has_more: backend.meta.has_more,
    },
    links: backend.links,
  };
}

function toApiResponse<T>(item: T): ApiResponse<T> {
  return { data: item };
}

// ─── Fetch Wrapper ────────────────────────────────────
type RequestOptions = {
  method?: string;
  headers?: Record<string, string>;
  body?: unknown;
  params?: Record<string, string | number | boolean | string[] | undefined>;
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

// ─── API Client ───────────────────────────────────────
export const apiClient = {
  get: <T>(endpoint: string, params?: Record<string, string | number | boolean | string[] | undefined>) =>
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

// ─── Auth API ─────────────────────────────────────────
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

// ─── Tenant / Workspace API ───────────────────────────
// Backend tenant router is at /api/v1/tenants/workspaces
// Returns list of workspaces (not envelope)
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

// ─── Contacts API ─────────────────────────────────────
// Backend returns envelope {data, meta, links} for list/search
// and envelope {data: item} for single items.
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
    // Backend uses page/limit (not skip/limit)
    return apiClient
      .get<BackendListResponse<Contact>>('/api/v1/crm/contacts', {
        ...(params?.page ? { page: params.page } : {}),
        ...(params?.limit ? { limit: params.limit } : {}),
        ...(params?.search ? { search: params.search } : {}),
        ...(params?.stage ? { stage: params.stage } : {}),
        ...(params?.source ? { source: params.source } : {}),
      } as Record<string, string | number | boolean | undefined>)
      .then(toPaginated);
  },

  get: (id: string) =>
    apiClient.get<BackendListResponse<Contact>>(`/api/v1/crm/contacts/${id}`).then(
      (resp) => toApiResponse(resp.data[0])
    ),

  create: (data: CreateContactRequest) =>
    apiClient.post<BackendListResponse<Contact>>('/api/v1/crm/contacts', data).then(
      (resp) => toApiResponse(resp.data[0])
    ),

  update: (id: string, data: UpdateContactRequest) =>
    apiClient.patch<BackendListResponse<Contact>>(
      `/api/v1/crm/contacts/${id}`,
      data
    ).then((resp) => toApiResponse(resp.data[0])),

  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/contacts/${id}`),

  search: (query: string, params?: { limit?: number; offset?: number }) => {
    // Backend uses GET with query param and page/limit
    return apiClient
      .get<BackendListResponse<Contact>>('/api/v1/crm/contacts/search', {
        q: query,
        ...(params?.limit ? { limit: params.limit } : {}),
        ...(params?.offset ? { offset: params.offset } : {}),
      } as Record<string, string | number | boolean | undefined>)
      .then(toPaginated);
  },

  getActivities: (id: string) =>
    apiClient.get<BackendListResponse<Activity>>(
      `/api/v1/crm/contacts/${id}/activities`
    ).then((resp) => ({
      data: resp.data,
      meta: resp.meta,
      links: resp.links,
    } as PaginatedResponse<Activity>)),
};

// ─── Deals API ────────────────────────────────────────
export const dealsApi = {
  list: (params?: {
    page?: number;
    limit?: number;
    pipeline_id?: string;
    stage?: string;
    search?: string;
    sort?: string;
  }) => {
    return apiClient
      .get<BackendListResponse<Deal>>('/api/v1/crm/deals', {
        ...(params?.page ? { page: params.page } : {}),
        ...(params?.limit ? { limit: params.limit } : {}),
        ...(params?.pipeline_id ? { pipeline_id: params.pipeline_id } : {}),
        ...(params?.stage ? { stage: params.stage } : {}),
        ...(params?.search ? { search: params.search } : {}),
      } as Record<string, string | number | boolean | undefined>)
      .then(toPaginated);
  },

  get: (id: string) =>
    apiClient.get<BackendListResponse<Deal>>(`/api/v1/crm/deals/${id}`).then(
      (resp) => toApiResponse(resp.data[0])
    ),

  create: (data: CreateDealRequest) =>
    apiClient.post<BackendListResponse<Deal>>('/api/v1/crm/deals', data).then(
      (resp) => toApiResponse(resp.data[0])
    ),

  update: (id: string, data: UpdateDealRequest) =>
    apiClient.patch<BackendListResponse<Deal>>(
      `/api/v1/crm/deals/${id}`,
      data
    ).then((resp) => toApiResponse(resp.data[0])),

  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/deals/${id}`),
};

// ─── Pipelines API ────────────────────────────────────
export const pipelinesApi = {
  list: () =>
    apiClient.get<BackendListResponse<Pipeline>>('/api/v1/crm/pipelines').then(
      (resp) => ({
        data: resp.data,
        meta: resp.meta,
        links: resp.links,
      } as PaginatedResponse<Pipeline>)
    ),

  get: (id: string) =>
    apiClient.get<BackendListResponse<Pipeline>>(
      `/api/v1/crm/pipelines/${id}`
    ).then((resp) => toApiResponse(resp.data[0])),

  create: (data: CreatePipelineRequest) =>
    apiClient.post<BackendListResponse<Pipeline>>(
      '/api/v1/crm/pipelines',
      data
    ).then((resp) => toApiResponse(resp.data[0])),

  update: (id: string, data: Partial<CreatePipelineRequest>) =>
    apiClient.patch<BackendListResponse<Pipeline>>(
      `/api/v1/crm/pipelines/${id}`,
      data
    ).then((resp) => toApiResponse(resp.data[0])),

  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/pipelines/${id}`),

  reorderStages: (pipelineId: string, stageIds: string[]) =>
    apiClient
      .put<BackendListResponse<Pipeline>>(
        `/api/v1/crm/pipelines/${pipelineId}/stages/reorder`,
        { stage_ids: stageIds }
      )
      .then((resp) => toApiResponse(resp.data[0])),
};

// ─── Activities API ───────────────────────────────────
export const activitiesApi = {
  list: (params?: {
    page?: number;
    limit?: number;
    type?: string;
    subject?: string;
    contact_id?: string;
    deal_id?: string;
    user_id?: string;
    sort?: string;
  }) => {
    return apiClient
      .get<BackendListResponse<Activity>>('/api/v1/crm/activities', {
        ...(params?.page ? { page: params.page } : {}),
        ...(params?.limit ? { limit: params.limit } : {}),
        ...(params?.type ? { type: params.type } : {}),
        ...(params?.subject ? { subject: params.subject } : {}),
        ...(params?.contact_id ? { contact_id: params.contact_id } : {}),
        ...(params?.deal_id ? { deal_id: params.deal_id } : {}),
        ...(params?.user_id ? { user_id: params.user_id } : {}),
      } as Record<string, string | number | boolean | undefined>)
      .then(toPaginated);
  },

  get: (id: string) =>
    apiClient.get<BackendListResponse<Activity>>(
      `/api/v1/crm/activities/${id}`
    ).then((resp) => toApiResponse(resp.data[0])),

  create: (data: {
    workspace_id: string;
    type: string;
    subject: string;
    description?: string;
    contact_id?: string;
    deal_id?: string;
    user_id?: string;
  }) =>
    apiClient.post<BackendListResponse<Activity>>('/api/v1/crm/activities', data).then(
      (resp) => toApiResponse(resp.data[0])
    ),

  update: (id: string, data: Partial<{ type: string; subject: string; description?: string }>) =>
    apiClient.patch<BackendListResponse<Activity>>(
      `/api/v1/crm/activities/${id}`,
      data
    ).then((resp) => toApiResponse(resp.data[0])),

  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/crm/activities/${id}`),
};