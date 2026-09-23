import { NextRequest, NextResponse } from "next/server";

const publicPaths = new Set([
  "/",
  "/demo",
  "/icon.svg",
  "/login",
  "/api/auth/login",
  "/api/auth/register",
  "/api/auth/logout",
]);

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  if (publicPaths.has(pathname) || pathname.startsWith("/_next/") || pathname === "/favicon.ico") {
    return NextResponse.next();
  }

  const session = request.cookies.get("oh_user_session")?.value;
  if (session) {
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
