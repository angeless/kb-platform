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

class ApiClient {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
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
