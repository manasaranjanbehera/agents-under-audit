const windowMs = 60 * 60 * 1000;
const defaultLimit = Number(
  process.env.TRIAGE_RATE_LIMIT_PER_HOUR ?? process.env.DEMO_RATE_LIMIT_PER_HOUR ?? "5",
);

type Entry = {
  count: number;
  expiresAt: number;
};

const visits = new Map<string, Entry>();

export function checkRateLimit(
  key: string,
  options?: { limit?: number; windowMs?: number },
): { allowed: boolean; remaining: number } {
  const limit = options?.limit ?? defaultLimit;
  const window = options?.windowMs ?? windowMs;
  const now = Date.now();
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
