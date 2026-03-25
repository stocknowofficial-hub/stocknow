import { NextResponse } from "next/server";
import { sendVipInvite } from "@/lib/telegram";

function getDB() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    if (ctx?.env?.DB) return ctx.env.DB as import("@cloudflare/workers-types").D1Database;
  } catch {}
  return null;
}

function authOk(request: Request): boolean {
  const secret = process.env.CRON_SECRET;
  if (!secret) return false;
  return request.headers.get("Authorization") === `Bearer ${secret}`;
}

/**
 * POST /api/telegram/register
 * Worker의 /start 핸들러에서 호출 — 텔레그램 유저를 D1에 등록하고 무료 체험 부여
 */
export async function POST(request: Request) {
  if (!authOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { chat_id, name, username, ref } = await request.json();
  if (!chat_id) {
    return NextResponse.json({ error: "chat_id required" }, { status: 400 });
  }

  // ref = 텔레그램 봇 /start ref_XXXXXXXX 의 XXXXXXXX (referrer 텔레그램 chat_id)
  const referrerTelegramId = ref ? String(ref) : null;

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB error" }, { status: 500 });

  const userId = `telegram_${chat_id}`;
  const telegramName = username ? `${name} (@${username})` : name;

  // 1. users 테이블에 upsert (이미 있으면 이름만 업데이트)
  await db
    .prepare(
      `INSERT INTO users (id, id_type, telegram_id, telegram_name, name)
       VALUES (?, 'telegram', ?, ?, ?)
       ON CONFLICT(id) DO UPDATE SET
         telegram_name = excluded.telegram_name,
         name = excluded.name,
         updated_at = CURRENT_TIMESTAMP`
    )
    .bind(userId, String(chat_id), telegramName, name ?? "")
    .run();

  // 2. subscriptions — 이미 있으면 건드리지 않음 (재가입 방지)
  const existing = await db
    .prepare("SELECT plan, status, expires_at FROM subscriptions WHERE user_id = ?")
    .bind(userId)
    .first<{ plan: string; status: string; expires_at: string | null }>();

  let isNewTrial = false;

  if (!existing) {
    await db
      .prepare(
        `INSERT INTO subscriptions (user_id, plan, status, expires_at)
         VALUES (?, 'trial', 'active', datetime('now', '+7 days'))`
      )
      .bind(userId)
      .run();
    isNewTrial = true;

    // 추천인 처리: telegram_id 컬럼 OR telegram_ prefix ID로 조회
    // (웹 계정에 텔레그램 연동한 경우도 찾기 위해 telegram_id 컬럼 우선 조회)
    if (referrerTelegramId) {
      const referrerExists = await db
        .prepare("SELECT id FROM users WHERE telegram_id = ? OR id = ? LIMIT 1")
        .bind(referrerTelegramId, `telegram_${referrerTelegramId}`)
        .first<{ id: string }>();
      const referrerId = referrerExists?.id ?? `telegram_${referrerTelegramId}`;

      if (referrerExists && referrerId !== userId) {
        const alreadyReferred = await db
          .prepare("SELECT id FROM referrals WHERE referrer_id = ? AND referee_id = ?")
          .bind(referrerId, userId)
          .first();

        const referrerCount = await db
          .prepare("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id = ? AND rewarded = 1")
          .bind(referrerId)
          .first<{ cnt: number }>();

        if (!alreadyReferred && (referrerCount?.cnt ?? 0) < 20) {
          await db
            .prepare("UPDATE users SET referred_by = ? WHERE id = ?")
            .bind(referrerId, userId)
            .run();

          await db
            .prepare("INSERT INTO referrals (referrer_id, referee_id, rewarded) VALUES (?, ?, 1)")
            .bind(referrerId, userId)
            .run();

          // referrer 구독 +7일 연장 (추천인 보상만, referee는 trial 그대로)
          await db
            .prepare(
              `UPDATE subscriptions
               SET expires_at = COALESCE(datetime(expires_at, '+7 days'), datetime('now', '+7 days')),
                   updated_at = CURRENT_TIMESTAMP
               WHERE user_id = ?`
            )
            .bind(referrerId)
            .run();
        }
      }
    }
  }

  const sub = existing ?? { plan: "trial", status: "active", expires_at: null };
  const isActive = sub.status === "active" && sub.plan !== "free";

  // 3. VIP 초대 링크 발송 (신규 trial 또는 기존 유료/trial 활성 유저)
  if (isNewTrial || isActive) {
    const expiresAt = isNewTrial
      ? new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()
      : sub.expires_at;

    await sendVipInvite(
      String(chat_id),
      name ?? "회원",
      sub.plan === "trial" ? "7일 무료 체험" : sub.plan.toUpperCase(),
      expiresAt
    );
  }

  console.log(`[Telegram Register] ${isNewTrial ? "신규 체험" : "기존 유저"} — ${name} (${chat_id})`);
  return NextResponse.json({ ok: true, isNewTrial, inviteSent: isNewTrial || isActive });
}
