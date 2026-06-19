// ─── Media API ─────────────────────────────────────────────
// Backend routes: /api/v1/media/...

import { apiClient } from '@/lib/api';
import type { ApiResponse, PaginatedResponse } from '@/types';

// ─── Types ─────────────────────────────────────────────────

export type MediaType = 'image' | 'video' | 'document' | 'audio' | 'other';

export type MediaStatus = 'uploading' | 'processing' | 'ready' | 'failed';

export interface MediaAsset {
  id: string;
  workspace_id: string;
  filename: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  media_type: MediaType;
  status: MediaStatus;
  url: string;
  thumbnail_url?: string;
  width?: number;
  height?: number;
  duration_seconds?: number;
  alt_text?: string;
  tags: string[];
  folder?: string;
  metadata: Record<string, unknown>;
  uploaded_by: string;
  created_at: string;
  updated_at: string;
}

export interface MediaUploadRequest {
  file: File | Blob;
  folder?: string;
  tags?: string[];
  alt_text?: string;
  metadata?: Record<string, unknown>;
}

export interface MediaUpdateRequest {
  alt_text?: string;
  tags?: string[];
  folder?: string;
  metadata?: Record<string, unknown>;
}

export interface MediaFolder {
  id: string;
  workspace_id: string;
  name: string;
  path: string;
  parent_id?: string;
  item_count: number;
  total_size: number;
  created_at: string;
}

export interface MediaUploadResult {
  id: string;
  url: string;
  thumbnail_url?: string;
  filename: string;
  size_bytes: number;
  mime_type: string;
}

// ─── Media API Client ──────────────────────────────────────

export const mediaApi = {
  // ── Upload ──

  /** Upload a single file (multipart/form-data) */
  upload: async (data: MediaUploadRequest): Promise<ApiResponse<MediaUploadResult>> => {
    const formData = new FormData();
    formData.append('file', data.file);
    if (data.folder) formData.append('folder', data.folder);
    if (data.alt_text) formData.append('alt_text', data.alt_text);
    if (data.tags) formData.append('tags', JSON.stringify(data.tags));
    if (data.metadata) formData.append('metadata', JSON.stringify(data.metadata));

    const result = await fetch('/api/v1/media/upload', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${JSON.parse(localStorage.getItem('auth-store') || '{}')?.state?.token || ''}`,
      },
      body: formData,
    });

    if (!result.ok) {
      throw new Error(`Upload failed: ${result.statusText}`);
    }

    return { data: await result.json() };
  },

  /** Upload multiple files */
  uploadMultiple: async (files: MediaUploadRequest[]): Promise<ApiResponse<MediaUploadResult[]>> => {
    const formData = new FormData();
    files.forEach((f, i) => {
      formData.append(`files`, f.file);
      if (f.folder) formData.append(`folder_${i}`, f.folder);
    });

    const result = await fetch('/api/v1/media/upload/multiple', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${JSON.parse(localStorage.getItem('auth-store') || '{}')?.state?.token || ''}`,
      },
      body: formData,
    });

    if (!result.ok) {
      throw new Error(`Upload failed: ${result.statusText}`);
    }

    return { data: await result.json() };
  },

  // ── List / Search ──

  /** List media assets */
  list: (params?: {
    page?: number;
    limit?: number;
    media_type?: MediaType;
    folder?: string;
    search?: string;
    tags?: string[];
    sort?: string;
  }) =>
    apiClient
      .get<{ items: MediaAsset[]; total: number; page: number; page_size: number }>(
        '/api/v1/media',
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
      })) as Promise<PaginatedResponse<MediaAsset>>,

  // ── Single Asset ──

  /** Get media asset details */
  get: (id: string) =>
    apiClient.get<MediaAsset>(`/api/v1/media/${id}`).then(
      (data) => ({ data }) as ApiResponse<MediaAsset>
    ),

  /** Update media asset metadata */
  update: (id: string, data: MediaUpdateRequest) =>
    apiClient.patch<MediaAsset>(`/api/v1/media/${id}`, data).then(
      (data) => ({ data }) as ApiResponse<MediaAsset>
    ),

  /** Delete media asset */
  delete: (id: string) =>
    apiClient.delete<void>(`/api/v1/media/${id}`),

  // ── Thumbnails ──

  /** Get thumbnail URL for an asset */
  getThumbnailUrl: (id: string, size?: 'sm' | 'md' | 'lg') =>
    size ? `/api/v1/media/${id}/thumbnail?size=${size}` : `/api/v1/media/${id}/thumbnail`,

  /** Regenerate thumbnail */
  regenerateThumbnail: (id: string) =>
    apiClient.post<{ thumbnail_url: string }>(`/api/v1/media/${id}/thumbnail/regenerate`).then(
      (data) => ({ data }) as ApiResponse<{ thumbnail_url: string }>
    ),

  // ── Folders ──

  /** List folders */
  listFolders: (parentId?: string) =>
    apiClient
      .get<MediaFolder[]>(parentId ? `/api/v1/media/folders?parent_id=${parentId}` : '/api/v1/media/folders')
      .then((items) => ({ data: items }) as unknown as ApiResponse<MediaFolder[]>),

  /** Create folder */
  createFolder: (name: string, parentId?: string) =>
    apiClient.post<MediaFolder>('/api/v1/media/folders', { name, parent_id: parentId }).then(
      (data) => ({ data }) as ApiResponse<MediaFolder>
    ),

  /** Delete folder */
  deleteFolder: (id: string) =>
    apiClient.delete<void>(`/api/v1/media/folders/${id}`),

  // ── Download ──

  /** Get download URL (signed) */
  getDownloadUrl: (id: string, expiresInMinutes?: number) =>
    apiClient
      .get<{ url: string; expires_at: string }>(`/api/v1/media/${id}/download`, {
        expires_in: expiresInMinutes ?? 60,
      } as Record<string, string | number | boolean | undefined>)
      .then((data) => ({ data }) as ApiResponse<{ url: string; expires_at: string }>),
};
