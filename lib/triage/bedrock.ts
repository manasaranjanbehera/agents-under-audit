import {
  BedrockRuntimeClient,
  ConverseCommand,
  ConverseCommandInput,
} from "@aws-sdk/client-bedrock-runtime";
import { settings } from "@/lib/triage/config";
import { ModelUsage } from "@/lib/triage/types";

const client = new BedrockRuntimeClient({
  region: settings.awsRegion,
  maxAttempts: 3,
});

export type ModelReply = {
  text: string;
  stopReason: string;
  usage: ModelUsage;
};

export async function converse({
  system,
  userText,
  useGuardrail = true,
}: {
  system: string;
  userText: string;
  useGuardrail?: boolean;
}): Promise<ModelReply> {
  const input: ConverseCommandInput = {
    modelId: settings.modelId,
    system: [{ text: system }],
    messages: [
      {
        role: "user",
        content: [{ text: userText }],
      },
    ],
    inferenceConfig: {
      maxTokens: settings.maxOutputTokens,
      temperature: 0,
    },
  };

  if (useGuardrail && settings.guardrailId) {
    input.guardrailConfig = {
      guardrailIdentifier: settings.guardrailId,
      guardrailVersion: settings.guardrailVersion ?? "DRAFT",
      trace: "enabled",
    };
  }

  const response = await client.send(new ConverseCommand(input));
  const contentBlocks = response.output?.message?.content ?? [];
  const text = contentBlocks
    .map((item) => ("text" in item ? item.text ?? "" : ""))
    .join("");

  return {
    text,
    stopReason: response.stopReason ?? "",
    usage: {
      calls: 1,
      inputTokens: response.usage?.inputTokens ?? 0,
      outputTokens: response.usage?.outputTokens ?? 0,
      latencyMs: response.metrics?.latencyMs ?? 0,
    },
  };
}
