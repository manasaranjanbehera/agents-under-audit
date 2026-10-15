import { NextResponse } from "next/server";
import { clearSessionCookieHeader } from "@/lib/server/session";

export async function POST() {
  const response = NextResponse.json({ ok: true });
  response.headers.set("Set-Cookie", clearSessionCookieHeader());
  return response;
}
