/**
 * Authentication state managed by zustand.
 * Stores JWT token and user info in localStorage + memory.
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
  logout: () => void;
  checkAuth: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  error: null,

  login: async (email, password) => {
    set({ isLoading: true, error: null });
    try {
      const resp = await api.post<{ access_token: string; user: User }>(
        "/v1/auth/login",
        { email, password },
      );
      localStorage.setItem("access_token", resp.data.access_token);
      set({ user: resp.data.user, isLoading: false });
    } catch (e) {
      const msg = e instanceof ApiClientError ? e.message : "登录失败";
      set({ error: msg, isLoading: false });
      throw e;
    }
  },

  register: async (tenantName, email, password) => {
    set({ isLoading: true, error: null });
    try {
      const resp = await api.post<{ access_token: string; user: User }>(
        "/v1/auth/register",
        { tenant_name: tenantName, email, password },
      );
      localStorage.setItem("access_token", resp.data.access_token);
      set({ user: resp.data.user, isLoading: false });
    } catch (e) {
      const msg = e instanceof ApiClientError ? e.message : "注册失败";
      set({ error: msg, isLoading: false });
      throw e;
    }
  },

  logout: () => {
    localStorage.removeItem("access_token");
    set({ user: null, error: null });
  },

  checkAuth: () => {
    const token = localStorage.getItem("access_token");
    if (!token) {
      set({ user: null });
      return;
    }
    // Decode JWT payload (not for security, just to show user info)
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      set({
        user: {
          id: payload.user_id,
          email: payload.email || "",
          role: payload.role || "",
          tenant_id: payload.tenant_id,
        },
      });
    } catch {
      localStorage.removeItem("access_token");
      set({ user: null });
    }
  },
}));
