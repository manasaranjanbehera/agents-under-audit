import { NextResponse } from "next/server";
import { readSessionCookie, verifySessionValue } from "@/lib/server/session";

export async function GET(request: Request) {
  const cookieHeader = request.headers.get("cookie");
  const rawSession = readSessionCookie(cookieHeader);
  const email = verifySessionValue(rawSession);
  return NextResponse.json({ email });
}
