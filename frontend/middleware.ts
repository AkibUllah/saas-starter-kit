import { NextResponse, type NextRequest } from "next/server";
import { resolveBackendUrl } from "@/lib/backend-url";

const BACKEND_URL = resolveBackendUrl(process.env.BACKEND_URL, process.env.BACKEND_HOSTPORT);
const PROTECTED = ["/dashboard", "/onboarding", "/admin", "/accept-invite"];
const AUTH_PAGES = ["/login", "/signup"];

function startsWithAny(path: string, prefixes: string[]): boolean {
  return prefixes.some((p) => path === p || path.startsWith(`${p}/`));
}

/** Copy Set-Cookie headers from the backend refresh response onto ours and into the request. */
function applySetCookies(from: Response, to: NextResponse, request: NextRequest): void {
  const setCookies: string[] =
    typeof (from.headers as unknown as { getSetCookie?: () => string[] }).getSetCookie === "function"
      ? (from.headers as unknown as { getSetCookie: () => string[] }).getSetCookie()
      : from.headers.get("set-cookie")?.split(/,(?=\s*\w+=)/) ?? [];
  for (const raw of setCookies) {
    to.headers.append("set-cookie", raw);
    const [pair] = raw.split(";");
    const [name, ...rest] = pair.split("=");
    request.cookies.set(name.trim(), rest.join("="));
  }
}

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const hasAccess = request.cookies.has("access_token");
  const hasRefresh = request.cookies.has("refresh_token");

  // Silent refresh: access cookie gone, refresh cookie present. Downstream Server
  // Components see the new cookies through the rewritten request headers.
  if (!hasAccess && hasRefresh) {
    try {
      const res = await fetch(`${BACKEND_URL}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { cookie: request.headers.get("cookie") ?? "" },
        cache: "no-store",
      });
      if (res.ok) {
        const next = NextResponse.next({ request: { headers: request.headers } });
        applySetCookies(res, next, request);
        next.headers.set("x-middleware-request-cookie", request.cookies.toString());
        return withAuthRedirects(request, next, true);
      }
    } catch {
      /* backend unreachable: fall through and treat as signed out */
    }
    const signedOut = NextResponse.redirect(new URL(`/login?next=${encodeURIComponent(pathname)}`, request.url));
    signedOut.cookies.delete("refresh_token");
    if (startsWithAny(pathname, PROTECTED)) return signedOut;
  }
  return withAuthRedirects(request, NextResponse.next(), hasAccess);
}

function withAuthRedirects(request: NextRequest, response: NextResponse, authenticated: boolean) {
  const { pathname, searchParams } = request.nextUrl;
  if (!authenticated && startsWithAny(pathname, PROTECTED)) {
    const url = new URL("/login", request.url);
    url.searchParams.set("next", pathname + (request.nextUrl.search || ""));
    return NextResponse.redirect(url);
  }
  if (authenticated && startsWithAny(pathname, AUTH_PAGES)) {
    const next = searchParams.get("next");
    return NextResponse.redirect(new URL(next && next.startsWith("/") ? next : "/dashboard", request.url));
  }
  return response;
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico|icon.svg|robots.txt).*)"],
};
