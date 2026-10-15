import { NextResponse } from "next/server";
import { z } from "zod";
import { sendAlertEmail } from "@/lib/server/alerts";
import { saveCaseRecord } from "@/lib/server/case-store";
import { checkRateLimit } from "@/lib/server/rate-limit";
import { readSessionCookie, verifySessionValue } from "@/lib/server/session";
import { estimateCostUsd } from "@/lib/triage/config";
import { decide } from "@/lib/triage/policy";
import { prescreen } from "@/lib/triage/prescreen";
import { runReader } from "@/lib/triage/reader";
import { conversationSchema } from "@/lib/triage/types";

export const runtime = "nodejs";
export const maxDuration = 30;

const requestSchema = z.object({
  conversation: conversationSchema,
});

export async function POST(request: Request) {
  const rawSession = readSessionCookie(request.headers.get("cookie"));
  const email = verifySessionValue(rawSession);
  if (!email) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }
  const limit = await checkRateLimit(email.toLowerCase());
  if (!limit.allowed) {
    return NextResponse.json(
      { error: "Rate limit exceeded. Try again in an hour." },
      { status: 429 },
    );
  }

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }
  const parsed = requestSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json(
      { error: "Invalid request payload", details: parsed.error.flatten() },
      { status: 400 },
    );
  }

  const conversation = parsed.data.conversation;
  const hits = prescreen(conversation);
  const reader = await runReader(conversation);
  const decision = decide(conversation.conversationId, hits, reader);
  const estimatedCostUsd = estimateCostUsd(reader.usage.inputTokens, reader.usage.outputTokens);
  let caseStoreSaved = true;
  let alertSent = decision.disposition === "close";

  try {
    await saveCaseRecord({ email, decision });
  } catch {
    caseStoreSaved = false;
  }

  if (email && decision.disposition !== "close") {
    try {
      await sendAlertEmail({
        to: email,
        decision,
      });
      alertSent = true;
    } catch {
      alertSent = false;
    }
  }

  return NextResponse.json({
    decision,
    reader: {
      promptVersion: reader.promptVersion,
      modelId: reader.modelId,
      error: reader.error,
      guardrailIntervened: reader.guardrailIntervened,
      groundedIndicators: reader.grounded,
      ungroundedIndicators: reader.ungrounded,
    },
    prescreenHits: hits,
    usage: reader.usage,
    estimatedCostUsd,
    remainingRunsThisHour: limit.remaining,
    operations: {
      caseStoreSaved,
      alertSent,
    },
  });
}
