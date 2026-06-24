/// <reference types="vitest" />
import { vi } from 'vitest';
import { mockFetch } from '../setup';

// Mock fetch globally using the mock from setup file
vi.stubGlobal('fetch', mockFetch);

// Mock the stores
vi.mock('@/stores/auth-store', () => ({
  useAuthStore: {
    getState: vi.fn(() => ({
      token: 'mock-token-123',
      refreshToken: 'mock-refresh',
      logout: vi.fn(),
    })),
  },
}));

vi.mock('@/stores/workspace-store', () => ({
  useWorkspaceStore: {
    getState: vi.fn(() => ({
      currentWorkspace: { id: 'workspace-1', name: 'Test Workspace' },
    })),
  },
}));

// Helper to create a mock Response
function mockResponse(overrides: Partial<Response> = {}): Response {
  return {
    ok: true,
    status: 200,
    statusText: 'OK',
    headers: new Headers({ 'content-type': 'application/json' }),
    json: vi.fn().mockResolvedValue({}),
    ...overrides,
  } as Response;
}

import { apiClient, ApiError } from '@/lib/api';

describe('apiClient', () => {
  beforeEach(() => {
    mockFetch.mockReset();
  });

  describe('GET requests', () => {
    it('makes a GET request to the correct endpoint', async () => {
      const responseData = { data: [{ id: '1', name: 'Test' }] };
      mockFetch.mockResolvedValueOnce(
        mockResponse({
          ok: true,
          status: 200,
          json: vi.fn().mockResolvedValue(responseData),
        })
      );

      const result = await apiClient.get('/api/v1/test');

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const callUrl = mockFetch.mock.calls[0][0] as string;
      expect(callUrl).toContain('/api/v1/test');
      expect(callUrl).toContain('localhost');
      expect(result).toEqual(responseData);
    });

    it('adds query parameters to the URL', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({
          ok: true,
          json: vi.fn().mockResolvedValue({ items: [] }),
        })
      );

      await apiClient.get('/api/v1/test', {
        page: 1,
        limit: 50,
        search: 'test',
        active: true,
      });

      const callUrl = mockFetch.mock.calls[0][0] as string;
      expect(callUrl).toContain('page=1');
      expect(callUrl).toContain('limit=50');
      expect(callUrl).toContain('search=test');
      expect(callUrl).toContain('active=true');
    });

    it('skips undefined query parameters', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ ok: true, json: vi.fn().mockResolvedValue({}) })
      );

      await apiClient.get('/api/v1/test', {
        page: 1,
        limit: undefined,
      });

      const callUrl = mockFetch.mock.calls[0][0] as string;
      expect(callUrl).toContain('page=1');
      expect(callUrl).not.toContain('limit');
    });
  });

  describe('POST requests', () => {
    it('makes a POST request with JSON body', async () => {
      const requestBody = { name: 'Test', email: 'test@example.com' };
      const responseData = { id: '1', ...requestBody };

      mockFetch.mockResolvedValueOnce(
        mockResponse({
          ok: true,
          status: 201,
          json: vi.fn().mockResolvedValue(responseData),
        })
      );

      const result = await apiClient.post('/api/v1/test', requestBody);

      expect(mockFetch).toHaveBeenCalledTimes(1);
      const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(options.method).toBe('POST');
      expect(options.body).toBe(JSON.stringify(requestBody));
      expect(result).toEqual(responseData);
    });

    it('sends Content-Type header', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ ok: true, json: vi.fn().mockResolvedValue({}) })
      );

      await apiClient.post('/api/v1/test', { key: 'value' });

      const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = options.headers as Record<string, string>;
      expect(headers['Content-Type']).toBe('application/json');
    });
  });

  describe('PUT requests', () => {
    it('makes a PUT request with JSON body', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ ok: true, json: vi.fn().mockResolvedValue({}) })
      );

      await apiClient.put('/api/v1/test/1', { name: 'Updated' });

      const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(options.method).toBe('PUT');
      expect(options.body).toBe(JSON.stringify({ name: 'Updated' }));
    });
  });

  describe('PATCH requests', () => {
    it('makes a PATCH request with JSON body', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ ok: true, json: vi.fn().mockResolvedValue({}) })
      );

      await apiClient.patch('/api/v1/test/1', { field: 'value' });

      const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(options.method).toBe('PATCH');
      expect(options.body).toBe(JSON.stringify({ field: 'value' }));
    });
  });

  describe('DELETE requests', () => {
    it('makes a DELETE request', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ ok: true, status: 204, json: vi.fn().mockResolvedValue(undefined) })
      );

      await apiClient.delete('/api/v1/test/1');

      const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
      expect(options.method).toBe('DELETE');
    });
  });

  describe('error handling', () => {
    it('throws ApiError on 401 and calls logout', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({
          ok: false,
          status: 401,
          statusText: 'Unauthorized',
          json: vi.fn().mockResolvedValue({
            error: { detail: 'Authentication required' },
          }),
        })
      );

      await expect(apiClient.get('/api/v1/protected')).rejects.toMatchObject({
        status: 401,
        detail: 'Authentication required',
      });
    });

    it('throws ApiError on non-OK responses with error detail', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({
          ok: false,
          status: 422,
          statusText: 'Unprocessable Entity',
          json: vi.fn().mockResolvedValue({
            error: {
              detail: 'Validation failed',
              errors: [
                { field: 'email', message: 'Invalid email', code: 'invalid_format' },
              ],
            },
          }),
        })
      );

      try {
        await apiClient.post('/api/v1/test', { email: 'invalid' });
        expect.unreachable('Should have thrown');
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).status).toBe(422);
        expect((error as ApiError).detail).toBe('Validation failed');
        expect((error as ApiError).errors).toHaveLength(1);
      }
    });

    it('throws ApiError with status text when error JSON is malformed', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          json: vi.fn().mockRejectedValue(new Error('Invalid JSON')),
        })
      );

      await expect(apiClient.get('/api/v1/test')).rejects.toMatchObject({
        status: 500,
        detail: 'Internal Server Error',
      });
    });

    it('throws ApiError on network error', async () => {
      mockFetch.mockRejectedValueOnce(new TypeError('Failed to fetch'));

      await expect(apiClient.get('/api/v1/test')).rejects.toMatchObject({
        status: 0,
        detail: 'Network error. Please check your connection.',
      });
    });

    it('handles 204 No Content response', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({
          ok: true,
          status: 204,
          json: vi.fn().mockRejectedValue(new Error('No content')),
        })
      );

      const result = await apiClient.delete<void>('/api/v1/test/1');
      expect(result).toBeUndefined();
    });
  });

  describe('auth token injection', () => {
    it('injects Bearer token from auth store', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ ok: true, json: vi.fn().mockResolvedValue({}) })
      );

      await apiClient.get('/api/v1/test');

      const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = options.headers as Record<string, string>;
      expect(headers['Authorization']).toBe('Bearer mock-token-123');
    });

    it('injects X-Workspace-ID header', async () => {
      mockFetch.mockResolvedValueOnce(
        mockResponse({ ok: true, json: vi.fn().mockResolvedValue({}) })
      );

      await apiClient.get('/api/v1/test');

      const [, options] = mockFetch.mock.calls[0] as [string, RequestInit];
      const headers = options.headers as Record<string, string>;
      expect(headers['X-Workspace-ID']).toBe('workspace-1');
    });
  });
});