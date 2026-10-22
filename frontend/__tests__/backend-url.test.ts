import { describe, expect, it } from "vitest";
import { DEFAULT_BACKEND_URL, resolveBackendUrl } from "@/lib/backend-url";

describe("resolveBackendUrl", () => {
  it("prefers an explicit BACKEND_URL and trims trailing slashes", () => {
    expect(resolveBackendUrl("https://api.example.com/", "api:8000")).toBe("https://api.example.com");
  });

  it("builds an http URL from a Render host:port", () => {
    expect(resolveBackendUrl(undefined, "saas-api-x1y2:10000")).toBe("http://saas-api-x1y2:10000");
    expect(resolveBackendUrl("  ", "saas-api:8000")).toBe("http://saas-api:8000");
  });

  it("keeps a host:port value that already carries a scheme", () => {
    expect(resolveBackendUrl(undefined, "https://saas-api.onrender.com/")).toBe("https://saas-api.onrender.com");
  });

  it("falls back to the local API", () => {
    expect(resolveBackendUrl()).toBe(DEFAULT_BACKEND_URL);
    expect(resolveBackendUrl("", "")).toBe("http://localhost:8000");
  });
});
