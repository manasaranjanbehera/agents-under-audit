import { sql } from "@vercel/postgres";
import { TriageDecision } from "@/lib/triage/types";

function isDbEnabled(): boolean {
  return Boolean(process.env.POSTGRES_URL || process.env.POSTGRES_PRISMA_URL);
}

export async function saveCaseRecord({
  email,
  decision,
}: {
  email: string | null;
  decision: TriageDecision;
}): Promise<void> {
  if (!isDbEnabled()) {
    return;
  }

  await sql`
    CREATE TABLE IF NOT EXISTS case_records (
      id BIGSERIAL PRIMARY KEY,
      conversation_id TEXT NOT NULL,
      disposition TEXT NOT NULL,
      reasons JSONB NOT NULL,
      email TEXT,
      decided_at TIMESTAMPTZ NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
  `;

  await sql`
    INSERT INTO case_records (
      conversation_id,
      disposition,
      reasons,
      email,
      decided_at
    ) VALUES (
      ${decision.conversationId},
      ${decision.disposition},
      ${JSON.stringify(decision.reasons)},
      ${email},
      ${decision.decidedAt}
    )
  `;
}
