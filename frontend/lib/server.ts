/**
 * Server-side data access for Server Components and route handlers. Forwards the
 * browser's cookies to the backend; never used from the client bundle.
 */

import { cookies } from "next/headers";
import type { Org, User } from "./types";

export const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
export const ORG_COOKIE = "org_id";

function cookieHeader(): string {
  return cookies()
    .getAll()
    .map((c) => `${c.name}=${c.value}`)
    .join("; ");
}

export async function serverFetch<T>(path: string, init: RequestInit = {}): Promise<T | null> {
  const res = await fetch(`${BACKEND_URL}/api/v1${path}`, {
    ...init,
    headers: { cookie: cookieHeader(), accept: "application/json", ...(init.headers ?? {}) },
    cache: "no-store",
  });
  if (res.status === 401 || res.status === 403 || res.status === 404) return null;
  if (!res.ok) throw new Error(`backend ${res.status} for ${path}`);
  return (await res.json()) as T;
}

export async function getCurrentUser(): Promise<User | null> {
  if (!cookies().get("access_token")) return null;
  return serverFetch<User>("/users/me");
}

export async function getOrgs(): Promise<Org[]> {
  return (await serverFetch<Org[]>("/orgs")) ?? [];
}

/** Resolve the active org: cookie if still a member, otherwise the first org. */
export function pickCurrentOrg(orgs: Org[], cookieOrgId: string | undefined): Org | null {
  if (orgs.length === 0) return null;
  return orgs.find((o) => o.id === cookieOrgId) ?? orgs[0];
}
