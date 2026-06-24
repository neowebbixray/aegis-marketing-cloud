import { act, renderHook } from '@testing-library/react';
import { useAuthStore } from '@/stores/auth-store';

const makeMockUser = (overrides: Partial<{ id: string; email: string; display_name: string; roles: string[]; is_active: boolean }> = {}) => ({
  id: 'user-1',
  email: 'test@example.com',
  name: 'Test User',
  display_name: 'Test User',
  roles: ['admin'],
  is_active: true,
  ...overrides,
});

describe('auth-store', () => {
  beforeEach(() => {
    // Reset the store state between tests
    act(() => {
      useAuthStore.getState().logout();
    });
  });

  it('has initial state with no user and not authenticated', () => {
    const { result } = renderHook(() => useAuthStore());

    expect(result.current.user).toBeNull();
    expect(result.current.token).toBeNull();
    expect(result.current.refreshToken).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('login sets user, tokens, and authenticated state', () => {
    const { result } = renderHook(() => useAuthStore());

    const mockUser = makeMockUser();

    act(() => {
      result.current.login('access-token-123', 'refresh-token-456', mockUser);
    });

    expect(result.current.user).toEqual(mockUser);
    expect(result.current.token).toBe('access-token-123');
    expect(result.current.refreshToken).toBe('refresh-token-456');
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('login replaces previous user data', () => {
    const { result } = renderHook(() => useAuthStore());

    const firstUser = makeMockUser({ id: 'user-1', email: 'first@example.com', display_name: 'First User', roles: ['user'] });
    const secondUser = makeMockUser({ id: 'user-2', email: 'second@example.com', display_name: 'Second User' });

    act(() => {
      result.current.login('token-1', 'refresh-1', firstUser);
    });

    act(() => {
      result.current.login('token-2', 'refresh-2', secondUser);
    });

    expect(result.current.user?.id).toBe('user-2');
    expect(result.current.token).toBe('token-2');
    expect(result.current.refreshToken).toBe('refresh-2');
  });

  it('logout clears all state', () => {
    const { result } = renderHook(() => useAuthStore());

    // First login
    act(() => {
      result.current.login('token', 'refresh', makeMockUser());
    });
    expect(result.current.isAuthenticated).toBe(true);

    // Then logout
    act(() => {
      result.current.logout();
    });

    expect(result.current.token).toBeNull();
    expect(result.current.refreshToken).toBeNull();
    expect(result.current.user).toBeNull();
    expect(result.current.isAuthenticated).toBe(false);
  });

  it('setUser updates user without changing tokens', () => {
    const { result } = renderHook(() => useAuthStore());

    // First login
    act(() => {
      result.current.login('token-123', 'refresh-456', makeMockUser({ roles: ['user'] }));
    });

    // Update user
    const updatedUser = makeMockUser({ display_name: 'Updated User', roles: ['admin'] });

    act(() => {
      result.current.setUser(updatedUser);
    });

    expect(result.current.user?.display_name).toBe('Updated User');
    expect(result.current.token).toBe('token-123');
    expect(result.current.refreshToken).toBe('refresh-456');
  });

  it('setUser also sets isAuthenticated to true', () => {
    const { result } = renderHook(() => useAuthStore());

    expect(result.current.isAuthenticated).toBe(false);

    act(() => {
      result.current.setUser(makeMockUser({ roles: ['user'] }));
    });

    expect(result.current.isAuthenticated).toBe(true);
  });

  it('setTokens updates tokens without changing user', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.login('old-token', 'old-refresh', makeMockUser({ roles: ['user'] }));
    });

    act(() => {
      result.current.setTokens('new-token', 'new-refresh');
    });

    expect(result.current.token).toBe('new-token');
    expect(result.current.refreshToken).toBe('new-refresh');
    expect(result.current.user?.id).toBe('user-1');
    expect(result.current.isAuthenticated).toBe(true);
  });

  it('handles multiple logout calls safely', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.logout();
      result.current.logout();
      result.current.logout();
    });

    expect(result.current.isAuthenticated).toBe(false);
    expect(result.current.token).toBeNull();
  });

  it('handles login then setUser then setTokens in sequence', () => {
    const { result } = renderHook(() => useAuthStore());

    act(() => {
      result.current.login('token', 'refresh', makeMockUser({ roles: ['user'] }));
    });

    act(() => {
      result.current.setUser(makeMockUser({ email: 'updated@example.com', display_name: 'Updated User', roles: ['admin'] }));
    });

    act(() => {
      result.current.setTokens('new-token', 'new-refresh');
    });

    expect(result.current.user?.email).toBe('updated@example.com');
    expect(result.current.token).toBe('new-token');
    expect(result.current.refreshToken).toBe('new-refresh');
    expect(result.current.isAuthenticated).toBe(true);
  });
});
