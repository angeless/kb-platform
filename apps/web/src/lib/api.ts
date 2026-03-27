/**
 * API client for kb-platform backend.
 * All requests go through this module for consistent auth and error handling.
 */

import { getUserMessage } from "./error-messages";

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

let refreshPromise: Promise<boolean> | null = null;

class ApiClient {
  private async refreshAccessToken(): Promise<boolean> {
    try {
      const resp = await fetch(`${API_BASE}/v1/auth/refresh`, {
        method: "POST",
        credentials: "include",
      });
      return resp.ok;
    } catch {
      return false;
    }
  }

  async request<T>(path: string, options: RequestInit = {}): Promise<ApiResponse<T>> {
    const headers: Record<string, string> = {
      "X-Requested-With": "XMLHttpRequest",
      ...(options.headers as Record<string, string>),
    };

    // Don't set Content-Type for FormData (browser sets it with boundary)
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    let resp: Response;
    try {
      resp = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
        credentials: "include",
      });
    } catch {
      throw new ApiClientError("网络连接失败，请检查网络后重试", "NETWORK_ERROR", 0);
    }

    // 401 auto-refresh: skip for auth endpoints to avoid recursive refresh
    if (resp.status === 401 && !path.startsWith("/v1/auth/")) {
      if (!refreshPromise) {
        refreshPromise = this.refreshAccessToken().finally(() => {
          refreshPromise = null;
        });
      }

      const success = await refreshPromise;

      if (success) {
        const retryResp = await fetch(`${API_BASE}${path}`, {
          ...options,
          headers,
          credentials: "include",
        });
        const retryBody = await retryResp.json();
        if (!retryResp.ok) {
          const err = retryBody as ApiError;
          throw new ApiClientError(getUserMessage(err.error_code, err.message), err.error_code, retryResp.status);
        }
        return retryBody as ApiResponse<T>;
      }

      // Refresh failed — dispatch event for SessionGuard to handle
      if (typeof window !== "undefined") {
        window.dispatchEvent(new Event("session-expired"));
      }
      throw new ApiClientError("登录已过期，请重新登录", "TOKEN_EXPIRED", 401);
    }

    const body = await resp.json();

    if (!resp.ok) {
      const err = body as ApiError;
      throw new ApiClientError(getUserMessage(err.error_code, err.message), err.error_code, resp.status);
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

export interface UploadProgressOptions {
  onProgress?: (percent: number) => void;
  signal?: AbortSignal;
}

/**
 * Upload a file with real-time progress tracking using XMLHttpRequest.
 * Fetch API doesn't support upload progress events, so XHR is used here.
 */
export function uploadWithProgress(
  path: string,
  formData: FormData,
  options: UploadProgressOptions = {},
): Promise<ApiResponse<unknown>> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const url = `${API_BASE}${path}`;

    // Abort support
    if (options.signal) {
      options.signal.addEventListener("abort", () => {
        xhr.abort();
        reject(new ApiClientError("上传已取消", "UPLOAD_CANCELLED", 0));
      });
    }

    // Progress tracking
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && options.onProgress) {
        const percent = Math.round((e.loaded / e.total) * 100);
        options.onProgress(percent);
      }
    };

    xhr.onload = () => {
      try {
        const body = JSON.parse(xhr.responseText);
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(body as ApiResponse<unknown>);
        } else {
          const err = body as ApiError;
          reject(new ApiClientError(getUserMessage(err.error_code, err.message), err.error_code, xhr.status));
        }
      } catch {
        reject(new ApiClientError(getUserMessage("PARSE_ERROR"), "PARSE_ERROR", xhr.status));
      }
    };

    xhr.onerror = () => {
      reject(new ApiClientError(getUserMessage("NETWORK_ERROR"), "NETWORK_ERROR", 0));
    };

    xhr.open("POST", url);
    xhr.withCredentials = true;
    xhr.setRequestHeader("X-Requested-With", "XMLHttpRequest");
    xhr.send(formData);
  });
}

export const api = new ApiClient();
