import { Resend } from "resend";
import { TriageDecision } from "@/lib/triage/types";

const resendApiKey = process.env.RESEND_API_KEY;
const from = process.env.ALERT_FROM_EMAIL;

const resend = resendApiKey ? new Resend(resendApiKey) : null;

export async function sendAlertEmail({
  to,
  decision,
}: {
  to: string;
  decision: TriageDecision;
}): Promise<void> {
  if (!resend || !from) {
    return;
  }

  const reasons = decision.reasons.slice(0, 10).map((item) => `- ${item}`).join("\n");
  await resend.emails.send({
    from,
    to,
    subject: `[Agents Under Audit] ${decision.disposition.toUpperCase()} ${decision.conversationId}`,
    text: `Conversation ${decision.conversationId} was classified as ${decision.disposition}.\n\nReasons:\n${reasons}\n\nThis alert intentionally excludes raw transcript text.`,
  });
}

export async function sendOtpEmail({ to, code }: { to: string; code: string }): Promise<void> {
  if (!resend || !from) {
    return;
  }

  await resend.emails.send({
    from,
    to,
    subject: "Your Agents Under Audit sign-in code",
    text: `Your one-time sign-in code is ${code}. It expires in 10 minutes.`,
  });
}
