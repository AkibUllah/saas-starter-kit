/**
 * Browser-side API client. Requests go to the same origin (`/api/v1/...`) where a
 * Next.js route handler proxies them to the backend with the auth cookies. On a
 * 401 for an expired access token it refreshes once and retries.
 */

import type { ApiErrorBody } from "./types";

export class ApiError extends Error {
  status: number;
  code: string | undefined;
  errors: { field: string; message: string }[] | undefined;

  constructor(status: number, body: ApiErrorBody) {
    super(body.detail);
    this.status = status;
    this.code = body.code;
    this.errors = body.errors;
  }

  fieldErrors(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const e of this.errors ?? []) out[e.field] = e.message;
    return out;
  }
}

export interface Fetcher {
  (input: string, init?: RequestInit): Promise<Response>;
}

let refreshing: Promise<boolean> | null = null;

export function createClient(fetchImpl: Fetcher = (...a) => fetch(...a), base = "/api/v1") {
  async function parseError(res: Response): Promise<ApiError> {
    let body: ApiErrorBody = { detail: res.statusText || "Request failed" };
    try {
      body = (await res.json()) as ApiErrorBody;
    } catch {
      /* non-JSON */
    }
    return new ApiError(res.status, body);
  }

  async function refresh(): Promise<boolean> {
    if (!refreshing) {
      refreshing = fetchImpl(`${base}/auth/refresh`, { method: "POST", credentials: "include" })
        .then((r) => r.ok)
        .catch(() => false)
        .finally(() => {
          refreshing = null;
        });
    }
    return refreshing;
  }

  async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
    const res = await fetchImpl(`${base}${path}`, {
      ...init,
      credentials: "include",
      headers: { "content-type": "application/json", ...(init.headers ?? {}) },
    });
    if (res.status === 401 && retry && !path.startsWith("/auth/")) {
      const err = await res.clone().json().catch(() => ({}) as ApiErrorBody);
      if ((err as ApiErrorBody).code === "token_expired" || (err as ApiErrorBody).code === "not_authenticated") {
        if (await refresh()) return request<T>(path, init, false);
      }
    }
    if (!res.ok) throw await parseError(res);
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  return {
    get: <T>(path: string) => request<T>(path),
    post: <T>(path: string, body?: unknown) =>
      request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
    patch: <T>(path: string, body: unknown) => request<T>(path, { method: "PATCH", body: JSON.stringify(body) }),
    delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  };
}

export const api = createClient();
export type ApiClient = ReturnType<typeof createClient>;
