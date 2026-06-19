import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User } from '@/types';

interface AuthState {
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  setUser: (user: User) => void;
  login: (token: string, refreshToken: string, user: User) => void;
  logout: () => void;
  setTokens: (token: string, refreshToken: string) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  token: null,
  refreshToken: null,
  isAuthenticated: false,

  setUser: (user) =>
    set({ user, isAuthenticated: true }),

  login: (token, refreshToken, user) =>
    set({
      token,
      refreshToken,
      user,
      isAuthenticated: true,
    }),

  logout: () =>
    set({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
    }),

  setTokens: (token, refreshToken) =>
    set({ token, refreshToken }),
}));
