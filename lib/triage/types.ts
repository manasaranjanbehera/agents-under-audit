import { z } from "zod";

export const MAX_MESSAGES = 200;
export const MAX_MESSAGE_CHARS = 4000;

export const messageSchema = z.object({
  sender: z.string().min(1).max(120),
  sentAt: z.string().datetime(),
  text: z.string().min(1).max(MAX_MESSAGE_CHARS),
});

export const conversationSchema = z.object({
  conversationId: z.string().regex(/^[A-Za-z0-9._-]{1,64}$/),
  channel: z.string().max(40),
  desk: z.string().max(40),
  participants: z.array(z.string().min(1).max(120)).max(50),
  messages: z.array(messageSchema).min(1).max(MAX_MESSAGES),
});

export const riskCategorySchema = z.enum([
  "concealment",
  "off_channel_communication",
  "coordinated_trading",
  "front_running",
  "mnpi_disclosure",
  "operational_issue",
]);

export const indicatorSchema = z.object({
  category: riskCategorySchema,
  message_index: z.number().int().nonnegative(),
  evidence: z.string().min(1).max(400),
});

export const readerFindingsSchema = z.object({
  summary: z.string().max(800),
  indicators: z.array(indicatorSchema).max(20).default([]),
  ai_directed_instruction: z.boolean(),
  ai_directed_message_indices: z.array(z.number().int().nonnegative()).max(MAX_MESSAGES).default([]),
});

export type Message = z.infer<typeof messageSchema>;
export type Conversation = z.infer<typeof conversationSchema>;
export type Indicator = z.infer<typeof indicatorSchema>;
export type ReaderFindings = z.infer<typeof readerFindingsSchema>;

export type ModelUsage = {
  calls: number;
  inputTokens: number;
  outputTokens: number;
  latencyMs: number;
};

export type ReaderOutcome = {
  findings: ReaderFindings | null;
  grounded: Indicator[];
  ungrounded: Indicator[];
  guardrailIntervened: boolean;
  error: string | null;
  promptVersion: string;
  modelId: string;
  usage: ModelUsage;
};

export type Disposition = "escalate" | "close" | "human_review";

export type TriageDecision = {
  conversationId: string;
  disposition: Disposition;
  reasons: string[];
  policyVersion: string;
  decidedAt: string;
};

export type PrescreenHit = {
  rule: string;
  messageIndex: number;
  match: string;
};
