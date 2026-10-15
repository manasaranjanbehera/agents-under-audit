import { Conversation, PrescreenHit } from "@/lib/triage/types";

const rules: Record<string, RegExp> = {
  addresses_automated_reviewer: /\b(?:ai|llm|chatbot|bot|reviewer|classifier)\b(?:\s+\w+){0,2}\s*:/i,
  role_prefix: /^\s*(?:system|assistant|developer)\s*:/i,
  override_prior_instructions:
    /\b(?:ignore|disregard|forget|override)\b.{0,30}\b(?:previous|prior|above|earlier)\b.{0,30}\b(?:instructions?|rules?|prompts?)\b/i,
  dictates_outcome:
    /\b(?:mark|classify|label|rate|approve|score)\b.{0,40}\b(?:low[- ]risk|benign|compliant|no[- ]risk)\b/i,
  suppresses_review:
    /\b(?:skip|bypass|avoid|suppress)\s+(?:the\s+)?(?:escalation|review|compliance|alert)\b/i,
};

export function prescreen(conversation: Conversation): PrescreenHit[] {
  const hits: PrescreenHit[] = [];
  conversation.messages.forEach((message, index) => {
    for (const [rule, pattern] of Object.entries(rules)) {
      const match = message.text.match(pattern);
      if (match) {
        hits.push({
          rule,
          messageIndex: index,
          match: match[0],
        });
      }
    }
  });
  return hits;
}
