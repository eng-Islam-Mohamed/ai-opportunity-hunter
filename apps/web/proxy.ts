import { NextRequest, NextResponse } from "next/server";

const publicPaths = new Set(["/login", "/api/auth/login", "/api/auth/logout"]);

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (publicPaths.has(pathname) || pathname.startsWith("/_next/") || pathname === "/favicon.ico") {
    return NextResponse.next();
  }

  const expectedSession = process.env.OPERATOR_SESSION_TOKEN;
  // Local development stays frictionless. Production is only made available
  // once its server-only operator credentials have been configured.
  if (process.env.NODE_ENV !== "production" && !expectedSession) {
    return NextResponse.next();
  }
  const session = request.cookies.get("oh_operator_session")?.value;
  if (expectedSession && session === expectedSession) {
    return NextResponse.next();
  }

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ detail: "Authentication required." }, { status: 401 });
  }

  const loginUrl = new URL("/login", request.url);
  loginUrl.searchParams.set("next", pathname + request.nextUrl.search);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ["/((?!_next/image|robots.txt).*)"],
};
