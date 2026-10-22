/**
 * Same-origin proxy: /api/v1/... -> BACKEND_URL/api/v1/...
 * Cookies, body and status pass through unchanged; Set-Cookie headers from the
 * backend (login, refresh, logout) reach the browser as first-party cookies.
 */

import { type NextRequest } from "next/server";

export const dynamic = "force-dynamic";

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const HOP_BY_HOP = new Set(["connection", "keep-alive", "transfer-encoding", "content-length", "host", "content-encoding"]);

async function proxy(request: NextRequest, { params }: { params: { path: string[] } }): Promise<Response> {
  const target = new URL(`/api/${params.path.join("/")}${request.nextUrl.search}`, BACKEND_URL);
  const headers = new Headers();
  request.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  const forwardedFor = request.headers.get("x-forwarded-for") ?? request.ip;
  if (forwardedFor) headers.set("x-forwarded-for", forwardedFor);

  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();
  const upstream = await fetch(target, { method: request.method, headers, body, redirect: "manual", cache: "no-store" });

  const responseHeaders = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase()) && key.toLowerCase() !== "set-cookie") responseHeaders.set(key, value);
  });
  const setCookies =
    typeof (upstream.headers as unknown as { getSetCookie?: () => string[] }).getSetCookie === "function"
      ? (upstream.headers as unknown as { getSetCookie: () => string[] }).getSetCookie()
      : [];
  for (const cookie of setCookies) responseHeaders.append("set-cookie", cookie);
  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as PUT, proxy as DELETE };
