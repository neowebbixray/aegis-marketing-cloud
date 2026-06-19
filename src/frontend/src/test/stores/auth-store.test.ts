import { act, renderHook } from '@testing-library/react';
import { useAuthStore } from '@/stores/auth-store';

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

    const mockUser = {
      id: 'user-1',
      email: 'test@example.com',
      display_name: 'Test User',
      roles: ['admin'],
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

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

    const firstUser = {
      id: 'user-1',
      email: 'first@example.com',
      display_name: 'First User',
      roles: ['user'],
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

    const secondUser = {
      id: 'user-2',
      email: 'second@example.com',
      display_name: 'Second User',
      roles: ['admin'],
      is_active: true,
      created_at: '2024-02-01T00:00:00Z',
      updated_at: '2024-02-01T00:00:00Z',
    };

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
      result.current.login('token', 'refresh', {
        id: 'user-1',
        email: 'test@example.com',
        display_name: 'Test User',
        roles: ['admin'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      });
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
      result.current.login('token-123', 'refresh-456', {
        id: 'user-1',
        email: 'test@example.com',
        display_name: 'Test User',
        roles: ['user'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      });
    });

    // Update user
    const updatedUser = {
      id: 'user-1',
      email: 'test@example.com',
      display_name: 'Updated User',
      roles: ['admin'],
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-02-01T00:00:00Z',
    };

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
      result.current.setUser({
        id: 'user-1',
        email: 'test@example.com',
        display_name: 'Test User',
        roles: ['user'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      });
    });

    expect(result.current.isAuthenticated).toBe(true);
  });

  it('setTokens updates tokens without changing user', () => {
    const { result } = renderHook(() => useAuthStore());

    const mockUser = {
      id: 'user-1',
      email: 'test@example.com',
      display_name: 'Test User',
      roles: ['user'],
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    };

    act(() => {
      result.current.login('old-token', 'old-refresh', mockUser);
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
      result.current.login('token', 'refresh', {
        id: 'user-1',
        email: 'test@example.com',
        display_name: 'Test User',
        roles: ['user'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      });
    });

    act(() => {
      result.current.setUser({
        id: 'user-1',
        email: 'updated@example.com',
        display_name: 'Updated User',
        roles: ['admin'],
        is_active: true,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-02-01T00:00:00Z',
      });
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
