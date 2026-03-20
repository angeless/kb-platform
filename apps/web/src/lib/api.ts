/**
 * API client for kb-platform backend.
 * All requests go through this module for consistent auth and error handling.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface ApiError {
  error_code: string;
  message: string;
  detail?: Record<string, unknown>;
}

export interface ApiResponse<T> {
  data: T;
  meta?: { request_id?: string; page?: number; page_size?: number; total?: number };
}

let refreshPromise: Promise<string | null> | null = null;

class ApiClient {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  private async refreshAccessToken(): Promise<string | null> {
    if (typeof window === "undefined") return null;
    const refreshToken = localStorage.getItem("refresh_token");
    if (!refreshToken) return null;

    try {
      const resp = await fetch(`${API_BASE}/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!resp.ok) {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        return null;
      }

      const body = await resp.json();
      const newToken: string = body.data?.access_token ?? body.access_token;
      localStorage.setItem("access_token", newToken);
      return newToken;
    } catch {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      return null;
    }
  }

  async request<T>(path: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    // Don't set Content-Type for FormData (browser sets it with boundary)
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const resp = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    // 401 auto-refresh: skip for auth endpoints to avoid recursive refresh
    if (resp.status === 401 && !path.startsWith("/v1/auth/")) {
      if (!refreshPromise) {
        refreshPromise = this.refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }

      const newToken = await refreshPromise;

      if (newToken) {
        headers["Authorization"] = `Bearer ${newToken}`;
        const retryResp = await fetch(`${API_BASE}${path}`, {
          ...options,
          headers,
        });
        const retryBody = await retryResp.json();
        if (!retryResp.ok) {
          const err = retryBody as ApiError;
          throw new ApiClientError(err.message || "请求失败", err.error_code, retryResp.status);
        }
        return retryBody as ApiResponse<T>;
      }

      // Refresh failed — redirect to login
      if (typeof window !== "undefined") {
        window.location.href = "/login";
      }
      throw new ApiClientError("登录已过期，请重新登录", "TOKEN_EXPIRED", 401);
    }

    const body = await resp.json();

    if (!resp.ok) {
      const err = body as ApiError;
      throw new ApiClientError(err.message || "请求失败", err.error_code, resp.status);
    }

    return body as ApiResponse<T>;
  }

  async get<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>(path, { method: "GET" });
  }

  async post<T>(path: string, data?: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      method: "POST",
      body: data instanceof FormData ? data : JSON.stringify(data),
    });
  }

  async put<T>(path: string, data: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  }

  async patch<T>(path: string, data: unknown): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async del<T>(path: string): Promise<ApiResponse<T>> {
    return this.request<T>(path, { method: "DELETE" });
  }
}

export class ApiClientError extends Error {
  constructor(
    message: string,
    public errorCode: string,
    public statusCode: number,
  ) {
    super(message);
    this.name = "ApiClientError";
  }
}

export const api = new ApiClient();
