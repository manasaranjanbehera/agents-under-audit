import { randomInt } from "crypto";

type OtpEntry = {
  code: string;
  expiresAt: number;
};

const pending = new Map<string, OtpEntry>();
const ttlMs = 10 * 60 * 1000;

export function issueOtp(email: string): string {
  const code = String(randomInt(100000, 1000000));
  pending.set(email.toLowerCase(), { code, expiresAt: Date.now() + ttlMs });
  return code;
}

export function verifyOtp(email: string, code: string): boolean {
  const key = email.toLowerCase();
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
