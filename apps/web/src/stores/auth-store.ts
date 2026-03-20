/**
 * Authentication state managed by zustand.
 * Tokens are stored in httpOnly cookies (managed by the backend).
 * This store only holds user info in memory.
 */

import { create } from "zustand";
import { api, ApiClientError } from "@/lib/api";

interface User {
  id: string;
  email: string;
  role: string;
  tenant_id: string;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  error: string | null;

  login: (email: string, password: string) => Promise<void>;
  register: (tenantName: string, email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      // Backend sets httpOnly cookies; response body still contains tokens for reference
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

  register: async (tenantName, email, password) => {
    set({ isLoading: true, error: null });
    try {
      await api.post("/v1/auth/register", { tenant_name: tenantName, email, password });
      // Register does not return tokens / set cookies — user must login after registration
      set({ isLoading: false });
    } catch (e) {
      const msg = e instanceof ApiClientError ? e.message : "注册失败";
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
    try {
      const resp = await api.get<User>("/v1/auth/me");
      set({ user: resp.data });
    } catch {
      set({ user: null });
    }
  },
}));
