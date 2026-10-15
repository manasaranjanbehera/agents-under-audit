import { NextResponse } from "next/server";
import { z } from "zod";
import { sendOtpEmail } from "@/lib/server/alerts";
import { issueOtp } from "@/lib/server/otp-store";
import { checkRateLimit } from "@/lib/server/rate-limit";

const schema = z.object({
  email: z.string().email(),
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
    return NextResponse.json({ error: "Invalid email." }, { status: 400 });
  }

  const email = parsed.data.email.toLowerCase();
  const otpLimit = await checkRateLimit(`otp:${email}`, { limit: 5, windowMs: 60 * 60 * 1000 });
  if (!otpLimit.allowed) {
    return NextResponse.json(
      { error: "Too many code requests. Try again in an hour." },
      { status: 429 },
    );
  }

  const code = await issueOtp(email);
  const hasEmailProvider = Boolean(process.env.RESEND_API_KEY && process.env.ALERT_FROM_EMAIL);

  if (process.env.NODE_ENV === "production" && !hasEmailProvider) {
    return NextResponse.json(
      { error: "Email provider is not configured." },
      { status: 503 },
    );
  }

  await sendOtpEmail({ to: email, code });

  // Local fallback: show code when email provider is not configured.
  const debugCode =
    process.env.NODE_ENV !== "production" && !hasEmailProvider
      ? code
      : undefined;

  return NextResponse.json({
    ok: true,
    debugCode,
  });
}
