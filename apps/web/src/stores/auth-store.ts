/**
 * Authentication state managed by zustand.
 * Tokens are stored in httpOnly cookies (managed by the backend via PA Pass).
 * This store only holds user info in memory.
 */

import { create } from "zustand";
import { api, ApiClientError } from "@/lib/api";

interface User {
  id: string;
  email: string;
  role: string;
  kb_id: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isCheckingAuth: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName?: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  isCheckingAuth: true,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      // Backend sets httpOnly cookies via PA Pass
      await api.post("/v1/auth/login", { email, password });
      // Fetch user info via /me endpoint (cookie is now set)
      const meResp = await api.get<User>("/v1/auth/me");
      set({ user: meResp.data, isLoading: false });
    } catch (e) {
      const msg = e instanceof ApiClientError ? e.message : "登录失败";
      set({ error: msg, isLoading: false });
      throw e;
    }
  },

  register: async (email, password, displayName?) => {
    set({ isLoading: true, error: null });
    try {
      await api.post("/v1/auth/register", {
        email,
        password,
        display_name: displayName || undefined,
      });
      // Register now auto-logs in (Pass sets cookie), fetch user info
      const meResp = await api.get<User>("/v1/auth/me");
      set({ user: meResp.data, isLoading: false });
    } catch (e) {
      let msg = "注册失败";
      if (e instanceof ApiClientError) {
        msg = e.message;
        const fields = e.detail?.fields as Record<string, string> | undefined;
        if (fields) {
          const firstField = Object.values(fields)[0];
          if (firstField) msg = firstField;
        }
      }
      set({ error: msg, isLoading: false });
      throw e;
    }
  },

  logout: async () => {
    try {
      await api.post("/v1/auth/logout");
    } catch {
      // Best-effort: even if the API call fails, clear local state
    }
    set({ user: null, error: null });
  },

  checkAuth: async () => {
    set({ isCheckingAuth: true });
    try {
      const resp = await api.get<User>("/v1/auth/me");
      set({ user: resp.data, isCheckingAuth: false });
    } catch {
      set({ user: null, isCheckingAuth: false });
    }
  },
}));
