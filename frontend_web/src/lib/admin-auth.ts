// 관리자 인증 유틸리티
// 쿠키 토큰 = HMAC-SHA256(ADMIN_PASSWORD + ADMIN_USERNAME, "stocknow_admin_session")

const COOKIE_NAME = "sn_admin_token";
const COOKIE_MAX_AGE = 60 * 60 * 8; // 8시간

async function computeToken(): Promise<string> {
  const secret = `${process.env.ADMIN_PASSWORD}:${process.env.ADMIN_USERNAME}:stocknow_admin_session`;
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode("valid")
  );
  return btoa(String.fromCharCode(...new Uint8Array(sig)));
}

export async function verifyAdminCookie(token: string | undefined): Promise<boolean> {
  if (!token) return false;
  try {
    const expected = await computeToken();
    return token === expected;
  } catch {
    return false;
  }
}

export async function createAdminCookieHeader(): Promise<string> {
  const token = await computeToken();
  return `${COOKIE_NAME}=${token}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=${COOKIE_MAX_AGE}`;
}

export function clearAdminCookieHeader(): string {
  return `${COOKIE_NAME}=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0`;
}

export { COOKIE_NAME };
