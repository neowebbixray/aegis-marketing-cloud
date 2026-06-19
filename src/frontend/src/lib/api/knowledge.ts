// ─── Knowledge API ─────────────────────────────────────────
// Backend routes: /api/v1/knowledge/...

import { apiClient } from '@/lib/api';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ─── Types ─────────────────────────────────────────────────

export type DocumentStatus = 'processing' | 'indexed' | 'failed';

export type DocumentSource = 'upload' | 'web_scrape' | 'integration' | 'api';

export type IndexingStatus = 'idle' | 'running' | 'completed' | 'failed';

export interface KnowledgeDocument {
  id: string;
  workspace_id: string;
  title: string;
  description?: string;
  content?: string;
  content_type: string;
  source: DocumentSource;
  source_url?: string;
  status: DocumentStatus;
  file_size?: number;
  file_url?: string;
  metadata: Record<string, unknown>;
  tags: string[];
  embedding_model?: string;
  chunk_count?: number;
  created_at: string;
  updated_at: string;
}

export interface DocumentUploadRequest {
  file?: File | Blob;
  title: string;
  description?: string;
  source_url?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface DocumentUpdateRequest {
  title?: string;
  description?: string;
  tags?: string[];
  metadata?: Record<string, unknown>;
}

export interface SearchQuery {
  query: string;
  filters?: {
    tags?: string[];
    content_type?: string;
    source?: DocumentSource;
    date_from?: string;
    date_to?: string;
  };
  limit?: number;
  offset?: number;
  min_score?: number;
}

export interface SearchResult {
  document_id: string;
  document_title: string;
  snippet: string;
  score: number;
  metadata: Record<string, unknown>;
  content_type: string;
}

export interface IndexingJob {
  id: string;
  workspace_id: string;
  status: IndexingStatus;
  total_documents: number;
  processed_documents: number;
  failed_documents: number;
  error_message?: string;
  started_at: string;
  completed_at?: string;
}

// ─── Knowledge API Client ──────────────────────────────────

export const knowledgeApi = {
  // ── Documents ──

  /** List knowledge documents */
  listDocuments: (params?: {
    page?: number;
    limit?: number;
    status?: DocumentStatus;
    source?: DocumentSource;
    tags?: string[];
    search?: string;
    sort?: string;
  }) =>
    apiClient
      .get<{ items: KnowledgeDocument[]; total: number; page: number; page_size: number }>(
        '/api/v1/knowledge/documents',
        {
          ...params,
          tags: params?.tags?.join(','),
        } as Record<string, string | number | boolean | undefined>
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
      })) as Promise<PaginatedResponse<KnowledgeDocument>>,

  /** Get document by ID */
  getDocument: (id: string) =>
    apiClient.get<KnowledgeDocument>(`/api/v1/knowledge/documents/${id}`).then(
      (data) => ({ data }) as ApiResponse<KnowledgeDocument>
    ),

  /** Upload a document (multipart/form-data) */
  uploadDocument: async (data: DocumentUploadRequest): Promise<ApiResponse<KnowledgeDocument>> => {
    const formData = new FormData();
    if (data.file) formData.append('file', data.file);
    formData.append('title', data.title);
    if (data.description) formData.append('description', data.description);
    if (data.source_url) formData.append('source_url', data.source_url);
    if (data.tags) formData.append('tags', JSON.stringify(data.tags));
    if (data.metadata) formData.append('metadata', JSON.stringify(data.metadata));

    const token = JSON.parse(localStorage.getItem('auth-store') || '{}')?.state?.token || '';
    const response = await fetch('/api/v1/knowledge/documents/upload', {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return { data: await response.json() };
  },

  /** Update document metadata */
  updateDocument: (id: string, data: DocumentUpdateRequest) =>
    apiClient.patch<KnowledgeDocument>(`/api/v1/knowledge/documents/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<KnowledgeDocument>
    ),

  /** Delete a document */
  deleteDocument: (id: string) =>
    apiClient.delete<void>(`/api/v1/knowledge/documents/${id}`),

  /** Get document content */
  getDocumentContent: (id: string) =>
    apiClient.get<string>(`/api/v1/knowledge/documents/${id}/content`).then(
      (data) => ({ data }) as ApiResponse<string>
    ),

  // ── Search ──

  /** Search across knowledge base */
  search: (query: SearchQuery) =>
    apiClient
      .post<{ items: SearchResult[]; total: number; offset: number }>(
        '/api/v1/knowledge/search',
        query
      )
      .then((res) => ({
        data: res.items,
        meta: {
          page: Math.floor(res.offset / (query.limit || 10)) + 1,
          per_page: query.limit || 10,
          total: res.total,
          has_more: res.offset + (query.limit || 10) < res.total,
        },
        links: { self: '' },
      })) as Promise<PaginatedResponse<SearchResult>>,

  /** Suggest search queries */
  suggest: (partial: string) =>
    apiClient.get<string[]>(`/api/v1/knowledge/search/suggest`, { q: partial } as Record<string, string | number | boolean | undefined>).then(
      (items) => ({ data: items }) as unknown as ApiResponse<string[]>
    ),

  // ── Indexing ──

  /** Trigger re-indexing */
  triggerReindex: () =>
    apiClient.post<IndexingJob>('/api/v1/knowledge/indexing/reindex').then(
      (data) => ({ data }) as ApiResponse<IndexingJob>
    ),

  /** Get indexing status */
  getIndexingStatus: () =>
    apiClient.get<IndexingJob>('/api/v1/knowledge/indexing/status').then(
      (data) => ({ data }) as ApiResponse<IndexingJob>
    ),

  /** List indexing history */
  listIndexingJobs: (params?: { page?: number; limit?: number }) =>
    apiClient
      .get<{ items: IndexingJob[]; total: number; page: number; page_size: number }>(
        '/api/v1/knowledge/indexing/jobs',
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
      })) as Promise<PaginatedResponse<IndexingJob>>,
};
