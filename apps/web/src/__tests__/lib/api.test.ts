import { describe, it, expect, vi, beforeEach } from "vitest";
import { ApiClientError } from "@/lib/api";

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
