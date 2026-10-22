/** Remembers the active organization in a cookie read by the dashboard layout. */

import { NextResponse, type NextRequest } from "next/server";

export async function POST(request: NextRequest): Promise<Response> {
  const { org_id } = (await request.json().catch(() => ({}))) as { org_id?: string };
  if (!org_id || !/^[a-f0-9]{32}$/.test(org_id)) {
    return NextResponse.json({ detail: "org_id required" }, { status: 400 });
  }
  const res = NextResponse.json({ ok: true });
  res.cookies.set("org_id", org_id, { path: "/", sameSite: "lax", httpOnly: true, maxAge: 60 * 60 * 24 * 365 });
  return res;
}
