import { PLANS } from "@/lib/plans";
import { sendVipInvite } from "@/lib/telegram";

function getDB() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    if (ctx?.env?.DB) return ctx.env.DB as import("@cloudflare/workers-types").D1Database;
  } catch {}
  return null;
}

export async function POST(request: Request) {
  let data: Record<string, string> = {};

  try {
    // Payapp는 application/x-www-form-urlencoded 또는 multipart/form-data로 전송
    const contentType = request.headers.get("content-type") || "";
    if (contentType.includes("application/x-www-form-urlencoded")) {
      const text = await request.text();
      data = Object.fromEntries(new URLSearchParams(text));
    } else {
      const formData = await request.formData();
      data = Object.fromEntries(
        Array.from(formData.entries()).map(([k, v]) => [k, String(v)])
      );
    }

    console.log("[Payment Webhook] Received:", JSON.stringify(data));

    // ── 1. 인증 검증 ──────────────────────────────────────────────
    // Payapp 실제 필드명: pay_state (결제상태), mul_no (결제고유번호), linkkey (연동KEY)
    const {
      userid,
      linkkey,
      pay_state,
      mul_no,
      price,
      var1: userId,
      var2: planId,
    } = data;

    // linkkey = 연동 KEY (PAYAPP_API_KEY) 로 검증
    if (
      userid !== process.env.PAYAPP_USER_ID ||
      linkkey !== process.env.PAYAPP_API_KEY
    ) {
      console.error("[Payment Webhook] Invalid credentials. userid:", userid, "linkkey match:", linkkey === process.env.PAYAPP_API_KEY);
      return new Response("Forbidden", { status: 403 });
    }

    // pay_state "4" = 결제 완료 (1=요청, 4=완료)
    if (pay_state !== "4") {
      console.log("[Payment Webhook] Non-complete state:", pay_state, "— skipping");
      return new Response("OK");
    }

    if (!userId || !planId || !mul_no) {
      console.error("[Payment Webhook] Missing required fields:", { userId, planId, mul_no });
      return new Response("Bad Request", { status: 400 });
    }

    // ── 2. 플랜 조회 ──────────────────────────────────────────────
    const plan = PLANS[planId];
    if (!plan) {
      console.error("[Payment Webhook] Unknown planId:", planId);
      return new Response("Unknown plan", { status: 400 });
    }

    const db = getDB();
    if (!db) {
      console.error("[Payment Webhook] D1 DB not found");
      return new Response("DB error", { status: 500 });
    }

    // ── 3. 중복 결제 방지 (mul_no 체크) ──────────────────────────
    const existing = await db
      .prepare("SELECT id FROM payments WHERE pay_id = ?")
      .bind(mul_no)
      .first();

    if (existing) {
      console.warn("[Payment Webhook] Duplicate mul_no:", mul_no);
      return new Response("OK"); // 이미 처리됨, 200 반환
    }

    // ── 4. 만료일 계산 ────────────────────────────────────────────
    const sub = await db
      .prepare("SELECT expires_at FROM subscriptions WHERE user_id = ?")
      .bind(userId)
      .first<{ expires_at: string | null }>();

    const now = new Date();
    let baseDate = now;
    if (sub?.expires_at) {
      const current = new Date(sub.expires_at);
      if (current > now) baseDate = current; // 남은 기간 보존
    }

    const newExpiry = new Date(baseDate);
    newExpiry.setMonth(newExpiry.getMonth() + plan.months);

    console.log(
      `[Payment Webhook] userId=${userId} planId=${planId} months=${plan.months} newExpiry=${newExpiry.toISOString()}`
    );

    // ── 5. subscriptions 업데이트 + payments 기록 (트랜잭션) ──────
    await db.batch([
      db
        .prepare(
          `INSERT INTO subscriptions (user_id, plan, status, expires_at, updated_at)
           VALUES (?, ?, 'active', ?, CURRENT_TIMESTAMP)
           ON CONFLICT(user_id) DO UPDATE SET
             plan       = excluded.plan,
             status     = 'active',
             expires_at = excluded.expires_at,
             updated_at = CURRENT_TIMESTAMP`
        )
        .bind(userId, plan.plan, newExpiry.toISOString()),

      db
        .prepare(
          `INSERT INTO payments (pay_id, user_id, plan_id, plan, amount, months)
           VALUES (?, ?, ?, ?, ?, ?)`
        )
        .bind(mul_no, userId, plan.id, plan.plan, Number(price), plan.months),
    ]);

    // ── 6. 추천인 보상 처리 ───────────────────────────────────────
    // 이 유저를 초대한 사람이 있고, 아직 보상을 안 받았다면 → rewarded = 1
    const referral = await db
      .prepare(
        `SELECT id, referrer_id FROM referrals WHERE referee_id = ? AND rewarded = 0 LIMIT 1`
      )
      .bind(userId)
      .first<{ id: number; referrer_id: string }>();

    if (referral) {
      // 추천인 구독 1개월 연장 + rewarded 플래그
      const referrerSub = await db
        .prepare("SELECT expires_at FROM subscriptions WHERE user_id = ?")
        .bind(referral.referrer_id)
        .first<{ expires_at: string | null }>();

      const referrerBase =
        referrerSub?.expires_at && new Date(referrerSub.expires_at) > now
          ? new Date(referrerSub.expires_at)
          : now;
      const referrerExpiry = new Date(referrerBase);
      referrerExpiry.setMonth(referrerExpiry.getMonth() + 1);

      await db.batch([
        db
          .prepare(
            `UPDATE subscriptions
             SET expires_at = ?, updated_at = CURRENT_TIMESTAMP
             WHERE user_id = ?`
          )
          .bind(referrerExpiry.toISOString(), referral.referrer_id),

        db
          .prepare("UPDATE referrals SET rewarded = 1 WHERE id = ?")
          .bind(referral.id),
      ]);

      console.log(
        `[Payment Webhook] Referral reward: referrer=${referral.referrer_id} newExpiry=${referrerExpiry.toISOString()}`
      );
    }

    // ── 7. VIP 채널 초대 링크 발송 ────────────────────────────────────
    const userRow = await db
      .prepare("SELECT telegram_id, name FROM users WHERE id = ?")
      .bind(userId)
      .first<{ telegram_id: string | null; name: string | null }>();

    if (userRow?.telegram_id) {
      await sendVipInvite(
        userRow.telegram_id,
        userRow.name ?? "회원",
        plan.plan.toUpperCase(),
        newExpiry.toISOString()
      );
    } else {
      console.log("[Payment Webhook] telegram_id 없음 — 텔레그램 연동 후 초대 링크 발송 예정");
    }

    console.log("[Payment Webhook] Done. mul_no:", mul_no);
    return new Response("OK");
  } catch (error) {
    console.error("[Payment Webhook] Exception:", error, "data:", JSON.stringify(data));
    return new Response("Internal Server Error", { status: 500 });
  }
}
