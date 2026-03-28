import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiClientError, api } from "@/lib/api";

describe("ApiClientError", () => {
  it("captures error code and status", () => {
    const err = new ApiClientError("Not found", "DOC_NOT_FOUND", 404);
    expect(err.message).toBe("Not found");
    expect(err.errorCode).toBe("DOC_NOT_FOUND");
    expect(err.statusCode).toBe(404);
    expect(err.name).toBe("ApiClientError");
  });

  it("is an instance of Error", () => {
    const err = new ApiClientError("fail", "ERROR", 500);
    expect(err).toBeInstanceOf(Error);
  });
});

describe("Cookie-based auth and token refresh", () => {
  const fetchMock = vi.fn();
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    globalThis.fetch = fetchMock;
    fetchMock.mockReset();
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it("sends credentials: include on all requests", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: { items: [] } }),
    });

    await api.get("/v1/documents");
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, options] = fetchMock.mock.calls[0];
    expect(options.credentials).toBe("include");
  });

  it("retries after 401 and successful cookie-based refresh", async () => {
    // First call: 401
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ error_code: "UNAUTHORIZED", message: "Token expired" }),
    });
    // Refresh call: success (backend sets new cookie)
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: { access_token: "new-token", token_type: "bearer" } }),
    });
    // Retry call: success
    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ data: { items: [] } }),
    });

    const result = await api.get("/v1/documents");
    expect(result.data).toEqual({ items: [] });

    // Verify refresh call uses credentials: include
    const refreshCall = fetchMock.mock.calls[1];
    expect(refreshCall[0]).toContain("/v1/auth/refresh");
    expect(refreshCall[1].credentials).toBe("include");

    // Verify retry also uses credentials: include
    const retryCall = fetchMock.mock.calls[2];
    expect(retryCall[1].credentials).toBe("include");
  });

  it("dispatches session-expired event on refresh failure", async () => {
    const expiredHandler = vi.fn();
    window.addEventListener("session-expired", expiredHandler);

    // First call: 401
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ error_code: "UNAUTHORIZED", message: "Token expired" }),
    });
    // Refresh call: failure
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ error_code: "INVALID_TOKEN", message: "Refresh token expired" }),
    });

    await expect(api.get("/v1/documents")).rejects.toThrow("登录已过期，请重新登录");
    expect(expiredHandler).toHaveBeenCalledTimes(1);

    window.removeEventListener("session-expired", expiredHandler);
  });

  it("does not refresh for auth endpoint 401", async () => {
    fetchMock.mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: async () => ({ error_code: "INVALID_CREDENTIALS", message: "Wrong password" }),
    });

    await expect(api.post("/v1/auth/login", { email: "a@b.com", password: "wrong" }))
      .rejects.toThrow("Wrong password");
    // Only 1 fetch call — no refresh attempted
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("shares refresh promise for concurrent 401s", async () => {
    // Both first calls: 401
    fetchMock.mockResolvedValueOnce({
      ok: false, status: 401,
      json: async () => ({ error_code: "UNAUTHORIZED", message: "expired" }),
    });
    fetchMock.mockResolvedValueOnce({
      ok: false, status: 401,
      json: async () => ({ error_code: "UNAUTHORIZED", message: "expired" }),
    });
    // Single refresh call
    fetchMock.mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({ data: { access_token: "shared-new-token", token_type: "bearer" } }),
    });
    // Two retry calls
    fetchMock.mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({ data: { result: "a" } }),
    });
    fetchMock.mockResolvedValueOnce({
      ok: true, status: 200,
      json: async () => ({ data: { result: "b" } }),
    });

    const [r1, r2] = await Promise.all([
      api.get("/v1/docs/1"),
      api.get("/v1/docs/2"),
    ]);

    expect(r1.data).toEqual({ result: "a" });
    expect(r2.data).toEqual({ result: "b" });
    const refreshCalls = fetchMock.mock.calls.filter(
      (c: any[]) => c[0].includes("/v1/auth/refresh")
    );
    expect(refreshCalls).toHaveLength(1);
  });
});
