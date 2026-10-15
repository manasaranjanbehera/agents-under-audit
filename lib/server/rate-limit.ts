import { sql } from "@vercel/postgres";

const windowMs = 60 * 60 * 1000;
const defaultLimit = Number(
  process.env.TRIAGE_RATE_LIMIT_PER_HOUR ?? process.env.DEMO_RATE_LIMIT_PER_HOUR ?? "5",
);

type Entry = {
  count: number;
  expiresAt: number;
};

const visits = new Map<string, Entry>();
let schemaReady: Promise<void> | null = null;

function isDbEnabled(): boolean {
  return Boolean(process.env.POSTGRES_URL || process.env.POSTGRES_PRISMA_URL);
}

async function ensureSchema(): Promise<void> {
  if (!isDbEnabled()) {
    return;
  }
  if (!schemaReady) {
    schemaReady = (async () => {
      await sql`
        CREATE TABLE IF NOT EXISTS rate_limits (
          key TEXT PRIMARY KEY,
          count INTEGER NOT NULL,
          expires_at TIMESTAMPTZ NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `;
    })();
  }
  await schemaReady;
}

export async function checkRateLimit(
  key: string,
  options?: { limit?: number; windowMs?: number },
): Promise<{ allowed: boolean; remaining: number }> {
  const limit = options?.limit ?? defaultLimit;
  const window = options?.windowMs ?? windowMs;
  const now = Date.now();

  if (isDbEnabled()) {
    await ensureSchema();
    const normalizedKey = key.toLowerCase();
    const existingResult = await sql<{
      count: number;
      expires_at: Date;
    }>`
      SELECT count, expires_at
      FROM rate_limits
      WHERE key = ${normalizedKey}
      LIMIT 1
    `;

    const entry = existingResult.rows[0];
    if (!entry || entry.expires_at.getTime() <= now) {
      await sql`
        INSERT INTO rate_limits (key, count, expires_at)
        VALUES (${normalizedKey}, 1, to_timestamp(${now + window} / 1000.0))
        ON CONFLICT (key)
        DO UPDATE SET
          count = 1,
          expires_at = EXCLUDED.expires_at,
          created_at = NOW()
      `;
      return { allowed: true, remaining: limit - 1 };
    }

    if (entry.count >= limit) {
      return { allowed: false, remaining: 0 };
    }

    const nextCount = entry.count + 1;
    await sql`
      UPDATE rate_limits
      SET count = ${nextCount}
      WHERE key = ${normalizedKey}
    `;
    return { allowed: true, remaining: Math.max(limit - nextCount, 0) };
  }

  const existing = visits.get(key);
  if (!existing || existing.expiresAt <= now) {
    visits.set(key, { count: 1, expiresAt: now + window });
    return { allowed: true, remaining: limit - 1 };
  }

  if (existing.count >= limit) {
    return { allowed: false, remaining: 0 };
  }

  existing.count += 1;
  visits.set(key, existing);
  return { allowed: true, remaining: Math.max(limit - existing.count, 0) };
}
