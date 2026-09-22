import { timingSafeEqual } from "node:crypto";
import { NextRequest, NextResponse } from "next/server";

function matchesSecret(supplied: string, expected: string) {
  const input = Buffer.from(supplied);
  const secret = Buffer.from(expected);
  return input.length === secret.length && timingSafeEqual(input, secret);
}

export async function POST(request: NextRequest) {
  const configuredPassword = process.env.OPERATOR_PASSWORD;
  const sessionToken = process.env.OPERATOR_SESSION_TOKEN;
  if (!configuredPassword || !sessionToken) {
    return NextResponse.json({ detail: "Operator access is not configured." }, { status: 503 });
  }

  const body = await request.json().catch(() => null);
  const password = typeof body?.password === "string" ? body.password : "";
  if (!matchesSecret(password, configuredPassword)) {
    return NextResponse.json({ detail: "Invalid password." }, { status: 401 });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: "oh_operator_session",
    value: sessionToken,
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "strict",
    maxAge: 60 * 60 * 12,
    path: "/",
  });
  return response;
}

