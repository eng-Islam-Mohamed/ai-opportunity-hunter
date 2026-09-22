import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const backend = process.env.BACKEND_API_URL;
  const internalToken = process.env.BACKEND_INTERNAL_TOKEN;
  if (!backend || !internalToken) return NextResponse.json({ detail: "Authentication is unavailable." }, { status: 503 });
  const upstream = await fetch(backend.replace(/\/$/, "") + "/api/v1/auth/register", { method: "POST", headers: { "content-type": "application/json", "x-internal-api-token": internalToken }, body: await request.text() });
  const result = await upstream.json();
  if (!upstream.ok) return NextResponse.json(result, { status: upstream.status });
  const response = NextResponse.json({ ok: true, email: result.email, daily_runs_remaining: result.daily_runs_remaining });
  response.cookies.set({ name: "oh_user_session", value: result.access_token, httpOnly: true, secure: process.env.NODE_ENV === "production", sameSite: "strict", maxAge: 60 * 60 * 24 * 7, path: "/" });
  return response;
}
