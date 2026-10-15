import { createHmac, timingSafeEqual } from "crypto";

const sessionSecret = process.env.SESSION_SECRET ?? "session-secret-change-me";
const sessionCookieName = "session";
const maxAgeSeconds = 60 * 60;
const defaultSecret = "session-secret-change-me";

export function isSessionConfigSafe(): boolean {
  return !(process.env.NODE_ENV === "production" && sessionSecret === defaultSecret);
}

function sign(payload: string): string {
  return createHmac("sha256", sessionSecret).update(payload).digest("hex");
}

export function createSessionValue(email: string): string {
  if (!isSessionConfigSafe()) {
    throw new Error("SESSION_SECRET must be set in production.");
  }
  const expires = Math.floor(Date.now() / 1000) + maxAgeSeconds;
  const payload = `${email}|${expires}`;
  return `${payload}|${sign(payload)}`;
}

export function verifySessionValue(raw: string | undefined): string | null {
  if (!isSessionConfigSafe()) {
    return null;
  }
  if (!raw) {
    return null;
  }
  const [email, expiresRaw, signature] = raw.split("|");
  if (!email || !expiresRaw || !signature) {
    return null;
  }
  const payload = `${email}|${expiresRaw}`;
  const expected = sign(payload);
  const actualBuffer = Buffer.from(signature);
  const expectedBuffer = Buffer.from(expected);
  if (actualBuffer.length !== expectedBuffer.length) {
    return null;
  }
  const isValid = timingSafeEqual(actualBuffer, expectedBuffer);
  if (!isValid) {
    return null;
  }
  const expires = Number(expiresRaw);
  if (!Number.isFinite(expires) || expires < Math.floor(Date.now() / 1000)) {
    return null;
  }
  return email;
}

export function sessionCookieHeader(value: string): string {
  const secureFlag = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `${sessionCookieName}=${value}; Path=/; HttpOnly; SameSite=Lax; Max-Age=${maxAgeSeconds}${secureFlag}`;
}

export function clearSessionCookieHeader(): string {
  const secureFlag = process.env.NODE_ENV === "production" ? "; Secure" : "";
  return `${sessionCookieName}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${secureFlag}`;
}

export function readSessionCookie(cookieHeader: string | null): string | undefined {
  if (!cookieHeader) {
    return undefined;
  }
  const parts = cookieHeader.split(";").map((item) => item.trim());
  const sessionPart = parts.find((part) => part.startsWith(`${sessionCookieName}=`));
  return sessionPart?.slice(sessionCookieName.length + 1);
}
