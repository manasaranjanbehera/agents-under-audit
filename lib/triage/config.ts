export const settings = {
  awsRegion: process.env.AWS_REGION ?? "us-east-1",
  modelId: process.env.BEDROCK_MODEL_ID ?? "amazon.nova-lite-v1:0",
  guardrailId: process.env.BEDROCK_GUARDRAIL_ID || undefined,
  guardrailVersion: process.env.BEDROCK_GUARDRAIL_VERSION || undefined,
  priceInputPer1k: Number(process.env.PRICE_INPUT_PER_1K ?? "0.00006"),
  priceOutputPer1k: Number(process.env.PRICE_OUTPUT_PER_1K ?? "0.00024"),
  maxOutputTokens: Number(process.env.MAX_OUTPUT_TOKENS ?? "600"),
};

export function estimateCostUsd(inputTokens: number, outputTokens: number): number {
  return (
    (inputTokens / 1000) * settings.priceInputPer1k +
    (outputTokens / 1000) * settings.priceOutputPer1k
  );
}
