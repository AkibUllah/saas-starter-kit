import { describe, expect, it, vi } from "vitest";
import { ApiError, createClient } from "@/lib/api";

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });

describe("api client", () => {
  it("parses JSON and sends credentials", async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ id: "u1" }));
    const client = createClient(fetchMock);
    await expect(client.get("/users/me")).resolves.toEqual({ id: "u1" });
    expect(fetchMock.mock.calls[0][0]).toBe("/api/v1/users/me");
    expect(fetchMock.mock.calls[0][1].credentials).toBe("include");
  });

  it("refreshes once on an expired token and retries the request", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json({ detail: "access token expired", code: "token_expired" }, 401))
      .mockResolvedValueOnce(json({ access_token: "new" }))
      .mockResolvedValueOnce(json([{ id: "p1" }]));
    const client = createClient(fetchMock);
    await expect(client.get("/orgs/x/projects")).resolves.toEqual([{ id: "p1" }]);
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual([
      "/api/v1/orgs/x/projects",
      "/api/v1/auth/refresh",
      "/api/v1/orgs/x/projects",
    ]);
  });

  it("gives up when the refresh fails and surfaces the ApiError", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(json({ detail: "access token expired", code: "token_expired" }, 401))
      .mockResolvedValueOnce(json({ detail: "invalid refresh token", code: "invalid_refresh" }, 401));
    const client = createClient(fetchMock);
    const err = await client.get("/users/me").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(401);
    expect((err as ApiError).code).toBe("token_expired");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("does not try to refresh auth endpoints and maps validation errors to fields", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      json({ detail: "validation failed", code: "validation_error", errors: [{ field: "password", message: "too weak" }] }, 422),
    );
    const client = createClient(fetchMock);
    const err = (await client.post("/auth/signup", {}).catch((e: unknown) => e)) as ApiError;
    expect(err.status).toBe(422);
    expect(err.fieldErrors()).toEqual({ password: "too weak" });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
