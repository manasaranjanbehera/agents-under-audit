import { NextResponse } from "next/server";
import { z } from "zod";
import { createSessionValue, sessionCookieHeader } from "@/lib/server/session";
import { verifyOtp } from "@/lib/server/otp-store";
import { checkRateLimit } from "@/lib/server/rate-limit";

const schema = z.object({
  email: z.string().email(),
  code: z.string().min(6).max(6),
});

export async function POST(request: Request) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }
  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "Invalid verification payload." }, { status: 400 });
  }

  const { email, code } = parsed.data;
  const verifyLimit = await checkRateLimit(`otp-verify:${email.toLowerCase()}`, {
    limit: 10,
    windowMs: 60 * 60 * 1000,
  });
  if (!verifyLimit.allowed) {
    return NextResponse.json(
      { error: "Too many verification attempts. Try again later." },
      { status: 429 },
    );
  }
  if (!(await verifyOtp(email, code))) {
    return NextResponse.json({ error: "Invalid or expired code." }, { status: 401 });
  }

  let sessionValue: string;
  try {
    sessionValue = createSessionValue(email);
  } catch (error) {
    return NextResponse.json(
      { error: error instanceof Error ? error.message : "Session configuration error." },
      { status: 500 },
    );
  }
  const response = NextResponse.json({ ok: true, email });
  response.headers.set("Set-Cookie", sessionCookieHeader(sessionValue));
  return response;
}
