import { renderHook, act, waitFor } from '@testing-library/react';
import { useAuth } from '@/lib/auth';
import { authApi } from '@/lib/api';

// Mock the API module
vi.mock('@/lib/api', () => ({
  authApi: {
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    refresh: vi.fn(),
    me: vi.fn(),
  },
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  ApiError: class MockApiError extends Error {
    status: number;
    detail: string;
    constructor(status: number, detail: string) {
      super(detail);
      this.name = 'ApiError';
      this.status = status;
      this.detail = detail;
    }
  },
}));

// Mock the auth store
const mockStoreLogin = vi.fn();
const mockStoreLogout = vi.fn();
const mockStoreSetTokens = vi.fn();
const mockStoreSetUser = vi.fn();

vi.mock('@/stores/auth-store', () => ({
  useAuthStore: Object.assign(
    (selector?: (state: unknown) => unknown) => {
      const state = {
        user: null,
        token: 'mock-token',
        refreshToken: 'mock-refresh',
        isAuthenticated: false,
        login: mockStoreLogin,
        logout: mockStoreLogout,
        setTokens: mockStoreSetTokens,
        setUser: mockStoreSetUser,
        getState: () => ({
          token: 'mock-token',
          refreshToken: 'mock-refresh',
          logout: mockStoreLogout,
          setTokens: mockStoreSetTokens,
          setUser: mockStoreSetUser,
        }),
      };
      return selector ? selector(state) : state;
    },
    { getState: () => ({ token: 'mock-token', refreshToken: 'mock-refresh', logout: mockStoreLogout, setTokens: mockStoreSetTokens, setUser: mockStoreSetUser }) }
  ),
}));

const makeMockUser = () => ({
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  display_name: 'Test User',
  roles: ['admin'],
  is_active: true,
});

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns initial auth state', () => {
    const { result } = renderHook(() => useAuth());

    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('calls login API and updates store on successful login', async () => {
    const mockTokens = {
      access_token: 'new-access-token',
      refresh_token: 'new-refresh-token',
      token_type: 'bearer',
      expires_in: 3600,
    };

    const mockUser = makeMockUser();

    vi.mocked(authApi.login).mockResolvedValueOnce(mockTokens);
    vi.mocked(authApi.me).mockResolvedValueOnce(mockUser);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      const user = await result.current.login({
        email: 'test@example.com',
        password: 'password123',
      });
      expect(user).toEqual(mockUser);
    });

    expect(authApi.login).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password123',
    });
    expect(authApi.me).toHaveBeenCalledTimes(1);
    expect(mockStoreLogin).toHaveBeenCalledWith(
      'new-access-token',
      'new-refresh-token',
      mockUser
    );
  });

  it('handles login failure', async () => {
    const loginError = new Error('Invalid credentials');
    vi.mocked(authApi.login).mockRejectedValueOnce(loginError);

    const { result } = renderHook(() => useAuth());

    await expect(
      act(async () => {
        await result.current.login({
          email: 'test@example.com',
          password: 'wrong-password',
        });
      })
    ).rejects.toThrow('Invalid credentials');

    expect(mockStoreLogin).not.toHaveBeenCalled();
  });

  it('calls logout API and clears store', async () => {
    vi.mocked(authApi.logout).mockResolvedValueOnce(undefined);

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      await result.current.logout();
    });

    expect(authApi.logout).toHaveBeenCalledTimes(1);
    expect(mockStoreLogout).toHaveBeenCalledTimes(1);
  });

  it('handles logout when API fails gracefully', async () => {
    vi.mocked(authApi.logout).mockRejectedValueOnce(new Error('Network error'));

    const { result } = renderHook(() => useAuth());

    await act(async () => {
      // Should not throw even if API fails
      await result.current.logout();
    });

    expect(mockStoreLogout).toHaveBeenCalledTimes(1);
  });

  it('refreshes session successfully', async () => {
    const mockTokens = {
      access_token: 'refreshed-access-token',
      refresh_token: 'refreshed-refresh-token',
      token_type: 'bearer',
      expires_in: 3600,
    };

    const mockUser = makeMockUser();

    vi.mocked(authApi.refresh).mockResolvedValueOnce(mockTokens);
    vi.mocked(authApi.me).mockResolvedValueOnce(mockUser);

    const { result } = renderHook(() => useAuth());

    let refreshedUser;
    await act(async () => {
      refreshedUser = await result.current.refreshSession();
    });

    expect(authApi.refresh).toHaveBeenCalledWith('mock-refresh');
    expect(mockStoreSetTokens).toHaveBeenCalledWith(
      'refreshed-access-token',
      'refreshed-refresh-token'
    );
    expect(mockStoreSetUser).toHaveBeenCalledWith(mockUser);
    expect(refreshedUser).toEqual(mockUser);
  });

  it('handles refresh failure by logging out', async () => {
    vi.mocked(authApi.refresh).mockRejectedValueOnce(new Error('Invalid token'));

    const { result } = renderHook(() => useAuth());

    let refreshedUser;
    await act(async () => {
      refreshedUser = await result.current.refreshSession();
    });

    expect(mockStoreLogout).toHaveBeenCalledTimes(1);
    expect(refreshedUser).toBeNull();
  });
});
