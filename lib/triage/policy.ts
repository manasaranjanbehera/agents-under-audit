import { PrescreenHit, ReaderOutcome, TriageDecision } from "@/lib/triage/types";

export const POLICY_VERSION = "triage-policy-v1";

const escalatingCategories = new Set([
  "concealment",
  "off_channel_communication",
  "coordinated_trading",
  "front_running",
  "mnpi_disclosure",
]);

export function decide(
  conversationId: string,
  prescreenHits: PrescreenHit[],
  reader: ReaderOutcome,
): TriageDecision {
  const escalate: string[] = [];
  const review: string[] = [];

  if (reader.guardrailIntervened) {
    escalate.push("guardrail_intervened");
  }

  prescreenHits.forEach((hit) => {
    escalate.push(`prescreen:${hit.rule}@${hit.messageIndex}`);
  });

  if (reader.findings) {
    if (reader.findings.ai_directed_instruction) {
      escalate.push("reader:ai_directed_instruction");
    }

    reader.grounded.forEach((item) => {
      if (escalatingCategories.has(item.category)) {
        escalate.push(`indicator:${item.category}@${item.message_index}`);
      }
    });

    reader.ungrounded.forEach((item) => {
      review.push(`ungrounded:${item.category}@${item.message_index}`);
    });
  } else if (!reader.guardrailIntervened) {
    review.push(`reader_failed:${reader.error ?? "unknown"}`);
  }

  const disposition = escalate.length
    ? "escalate"
    : review.length
      ? "human_review"
      : "close";
  const reasons = disposition === "close" ? ["no_escalating_findings"] : [...escalate, ...review];

  return {
    conversationId,
    disposition,
    reasons,
    policyVersion: POLICY_VERSION,
    decidedAt: new Date().toISOString(),
  };
}
