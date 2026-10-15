import { randomInt } from "crypto";
import { sql } from "@vercel/postgres";

type OtpEntry = {
  code: string;
  expiresAt: number;
};

const pending = new Map<string, OtpEntry>();
const ttlMs = 10 * 60 * 1000;
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
        CREATE TABLE IF NOT EXISTS otp_codes (
          email TEXT PRIMARY KEY,
          code TEXT NOT NULL,
          expires_at TIMESTAMPTZ NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
      `;
    })();
  }
  await schemaReady;
}

export async function issueOtp(email: string): Promise<string> {
  const code = String(randomInt(100000, 1000000));
  const key = email.toLowerCase();
  const expiresAt = Date.now() + ttlMs;

  const usedDb = isDbEnabled();
  if (usedDb) {
    await ensureSchema();
    await sql`
      INSERT INTO otp_codes (email, code, expires_at)
      VALUES (${key}, ${code}, to_timestamp(${expiresAt} / 1000.0))
      ON CONFLICT (email)
      DO UPDATE SET
        code = EXCLUDED.code,
        expires_at = EXCLUDED.expires_at,
        created_at = NOW()
    `;
  }

  if (!usedDb) {
    pending.set(key, { code, expiresAt });
  }
  return code;
}

export async function verifyOtp(email: string, code: string): Promise<boolean> {
  const key = email.toLowerCase();

  if (isDbEnabled()) {
    await ensureSchema();
    const nowMs = Date.now();
    const result = await sql<{
      code: string;
      expires_at: Date;
    }>`
      SELECT code, expires_at
      FROM otp_codes
      WHERE email = ${key}
      LIMIT 1
    `;

    const entry = result.rows[0];
    if (!entry) {
      return false;
    }
    if (entry.expires_at.getTime() < nowMs) {
      await sql`DELETE FROM otp_codes WHERE email = ${key}`;
      return false;
    }
    const ok = entry.code === code.trim();
    if (ok) {
      await sql`DELETE FROM otp_codes WHERE email = ${key}`;
    }
    return ok;
  }

  const entry = pending.get(key);
  if (!entry) {
    return false;
  }
  if (entry.expiresAt < Date.now()) {
    pending.delete(key);
    return false;
  }
  const ok = entry.code === code.trim();
  if (ok) {
    pending.delete(key);
  }
  return ok;
}
