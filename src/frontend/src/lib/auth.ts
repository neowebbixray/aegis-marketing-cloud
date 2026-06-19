import { useAuthStore } from '@/stores/auth-store';
import { useCallback } from 'react';
import type { LoginRequest, RegisterRequest, User, AuthTokens } from '@/types';
import { authApi } from './api';

export function useAuth() {
  const { user, isAuthenticated, login: storeLogin, logout: storeLogout } = useAuthStore();

  const login = useCallback(async (data: LoginRequest) => {
    const tokens = await authApi.login(data);
    // Fetch user profile after login
    const userResponse = await authApi.me();
    storeLogin(tokens.access_token, tokens.refresh_token, userResponse);
    return userResponse;
  }, [storeLogin]);

  const register = useCallback(async (data: RegisterRequest) => {
    // Backend returns TokenResponse for register — store tokens and fetch user
    const tokens = await authApi.register(data);
    storeLogin(tokens.access_token, tokens.refresh_token, null as unknown as User);
    return tokens;
  }, [storeLogin]);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore errors during logout
    }
    storeLogout();
  }, [storeLogout]);

  const refreshSession = useCallback(async () => {
    try {
      const refreshToken = useAuthStore.getState().refreshToken;
      if (!refreshToken) throw new Error('No refresh token');
      const tokens = await authApi.refresh(refreshToken);
      useAuthStore.getState().setTokens(tokens.access_token, tokens.refresh_token);
      const userResponse = await authApi.me();
      useAuthStore.getState().setUser(userResponse);
      return userResponse;
    } catch {
      storeLogout();
      return null;
    }
  }, [storeLogout]);

  return {
    user,
    isAuthenticated,
    login,
    register,
    logout,
    refreshSession,
  };
}
