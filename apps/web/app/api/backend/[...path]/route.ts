import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 300;

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const baseUrl = process.env.BACKEND_API_URL;
  const internalToken = process.env.BACKEND_INTERNAL_TOKEN;
  if (!baseUrl || !internalToken) {
    return NextResponse.json({ detail: "Backend connection is not configured." }, { status: 503 });
  }

  const { path } = await context.params;
  const upstream = new URL(path.join("/"), baseUrl.replace(/\/$/, "") + "/");
  upstream.search = request.nextUrl.search;
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("cookie");
  headers.delete("x-internal-api-token");
  headers.set("x-internal-api-token", internalToken);
  const userToken = request.cookies.get("oh_user_session")?.value;
  if (userToken) headers.set("authorization", "Bearer " + userToken);

  const response = await fetch(upstream, {
    method: request.method,
    headers,
    body: ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
    cache: "no-store",
  });
  const responseHeaders = new Headers(response.headers);
  responseHeaders.delete("set-cookie");
  return new NextResponse(response.body, { status: response.status, headers: responseHeaders });
}

export const GET = proxy;
export const POST = proxy;
