import { converse } from "@/lib/triage/bedrock";
import { settings } from "@/lib/triage/config";
import { READER_PROMPT_VERSION, READER_RETRY, READER_SYSTEM, renderTranscript } from "@/lib/triage/prompts";
import { Conversation, Indicator, ReaderOutcome, readerFindingsSchema } from "@/lib/triage/types";

const fencePattern = /^```(?:json)?\s*|\s*```$/gim;
const spacePattern = /\s+/g;

function parseFindings(text: string) {
  const cleaned = text.trim().replace(fencePattern, "");
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start === -1 || end <= start) {
    throw new Error("no JSON object in reply");
  }
  return readerFindingsSchema.parse(JSON.parse(cleaned.slice(start, end + 1)));
}

function normalize(text: string): string {
  return text.replace(spacePattern, " ").trim().toLowerCase();
}

function isGrounded(indicator: Indicator, conversation: Conversation): boolean {
  if (indicator.message_index >= conversation.messages.length) {
    return false;
  }
  const source = conversation.messages[indicator.message_index]?.text ?? "";
  return normalize(source).includes(normalize(indicator.evidence));
}

export async function runReader(conversation: Conversation, maxAttempts = 2): Promise<ReaderOutcome> {
  let usage = { calls: 0, inputTokens: 0, outputTokens: 0, latencyMs: 0 };
  let error: string | null = null;
  let prompt = renderTranscript(conversation);

  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    const reply = await converse({
      system: READER_SYSTEM,
      userText: prompt,
      useGuardrail: true,
    });
    usage = {
      calls: usage.calls + reply.usage.calls,
      inputTokens: usage.inputTokens + reply.usage.inputTokens,
      outputTokens: usage.outputTokens + reply.usage.outputTokens,
      latencyMs: usage.latencyMs + reply.usage.latencyMs,
    };

    if (reply.stopReason === "guardrail_intervened") {
      return {
        findings: null,
        grounded: [],
        ungrounded: [],
        guardrailIntervened: true,
        error: null,
        promptVersion: READER_PROMPT_VERSION,
        modelId: settings.modelId,
        usage,
      };
    }

    try {
      const findings = parseFindings(reply.text);
      const grounded = findings.indicators.filter((item) => isGrounded(item, conversation));
      const ungrounded = findings.indicators.filter((item) => !isGrounded(item, conversation));
      return {
        findings,
        grounded,
        ungrounded,
        guardrailIntervened: false,
        error: null,
        promptVersion: READER_PROMPT_VERSION,
        modelId: settings.modelId,
        usage,
      };
    } catch (err) {
      error = err instanceof Error ? err.message.split("\n")[0] : "invalid_model_output";
      prompt = `${renderTranscript(conversation)}\n\n${READER_RETRY.replace("{error}", error)}`;
    }
  }

  return {
    findings: null,
    grounded: [],
    ungrounded: [],
    guardrailIntervened: false,
    error,
    promptVersion: READER_PROMPT_VERSION,
    modelId: settings.modelId,
    usage,
  };
}
