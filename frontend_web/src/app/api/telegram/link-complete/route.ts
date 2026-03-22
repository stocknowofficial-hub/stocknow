import { NextResponse } from "next/server";

function getDB(): import("@cloudflare/workers-types").D1Database | null {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    if (ctx?.env?.DB) return ctx.env.DB;
  } catch {}
  const g = globalThis as any;
  return g.__CF_ENV_DB ?? (process.env as any).DB ?? null;
}

// 두 구독 중 더 좋은 것 반환 (paid > trial > free, 만료일 늦은 것 우선)
function betterSub(
  a: { plan: string; status: string; expires_at: string | null } | null,
  b: { plan: string; status: string; expires_at: string | null } | null
) {
  const rank = (plan: string) =>
    plan === "free" ? 0 : plan === "trial" ? 1 : 2; // paid plans = 2

  if (!a) return b;
  if (!b) return a;

  if (rank(a.plan) !== rank(b.plan)) {
    return rank(a.plan) > rank(b.plan) ? a : b;
  }
  // 같은 등급이면 만료일이 늦은 것
  const aExp = a.expires_at ? new Date(a.expires_at).getTime() : Infinity;
  const bExp = b.expires_at ? new Date(b.expires_at).getTime() : Infinity;
  return aExp >= bExp ? a : b;
}

export async function POST(request: Request) {
  try {
    const { token, chat_id, name, username } = await request.json();

    if (!token || !chat_id) {
      return NextResponse.json({ error: "Missing parameters" }, { status: 400 });
    }

    const db = getDB();
    console.log("[LinkComplete] DB found:", !!db, "| token:", token, "| chat_id:", chat_id);
    if (!db) return NextResponse.json({ error: "DB not available" }, { status: 500 });

    // 1. 토큰으로 웹 유저 확인
    const linkEntry = await db
      .prepare("SELECT user_id FROM telegram_link_tokens WHERE token = ?")
      .bind(token)
      .first<{ user_id: string }>();

    console.log("[LinkComplete] linkEntry:", linkEntry ? JSON.stringify(linkEntry) : "NOT FOUND");
    if (!linkEntry) {
      return NextResponse.json({ error: "Invalid or expired token" }, { status: 404 });
    }

    const webUserId = linkEntry.user_id as string;
    const telegramUserId = `telegram_${chat_id}`;
    const telegramName = username ? `${name} (@${username})` : name;

    // 2. 텔레그램 전용 계정 병합 처리
    const telegramOnlyUser = await db
      .prepare("SELECT id FROM users WHERE id = ?")
      .bind(telegramUserId)
      .first<{ id: string }>();

    if (telegramOnlyUser) {
      console.log("[LinkComplete] 텔레그램 전용 계정 발견 — 병합 시작:", telegramUserId);

      const webSub = await db
        .prepare("SELECT plan, status, expires_at FROM subscriptions WHERE user_id = ?")
        .bind(webUserId)
        .first<{ plan: string; status: string; expires_at: string | null }>();

      const tgSub = await db
        .prepare("SELECT plan, status, expires_at FROM subscriptions WHERE user_id = ?")
        .bind(telegramUserId)
        .first<{ plan: string; status: string; expires_at: string | null }>();

      const winner = betterSub(webSub, tgSub);

      // 웹 유저 구독을 더 좋은 것으로 업데이트
      if (winner) {
        await db
          .prepare(
            `INSERT INTO subscriptions (user_id, plan, status, expires_at, updated_at)
             VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
             ON CONFLICT(user_id) DO UPDATE SET
               plan = excluded.plan,
               status = excluded.status,
               expires_at = excluded.expires_at,
               updated_at = CURRENT_TIMESTAMP`
          )
          .bind(webUserId, winner.plan, winner.status, winner.expires_at)
          .run();
      }

      // 텔레그램 전용 계정 데이터 정리 후 삭제
      await db.batch([
        db.prepare("DELETE FROM subscriptions WHERE user_id = ?").bind(telegramUserId),
        db.prepare("DELETE FROM payments WHERE user_id = ?").bind(telegramUserId),
        db.prepare("DELETE FROM referrals WHERE referrer_id = ? OR referee_id = ?").bind(telegramUserId, telegramUserId),
        db.prepare("DELETE FROM users WHERE id = ?").bind(telegramUserId),
      ]);

      console.log("[LinkComplete] 병합 완료 — 텔레그램 계정 삭제:", telegramUserId);
    }

    // 3. 웹 유저에 telegram_id, telegram_name 저장
    await db
      .prepare(
        "UPDATE users SET telegram_id = ?, telegram_name = ?, name = COALESCE(name, ?), image = COALESCE(image, ?) WHERE id = ?"
      )
      .bind(chat_id, telegramName, name, "", webUserId)
      .run();

    // 4. 토큰 삭제
    await db
      .prepare("DELETE FROM telegram_link_tokens WHERE token = ?")
      .bind(token)
      .run();

    // 5. 구독 정보 반환 (VIP 초대 링크는 worker에서 성공 메시지 후 발송)
    const finalSub = await db
      .prepare("SELECT plan, status, expires_at FROM subscriptions WHERE user_id = ?")
      .bind(webUserId)
      .first<{ plan: string; status: string; expires_at: string | null }>();

    return NextResponse.json({
      success: true,
      userId: webUserId,
      plan: finalSub?.plan ?? "free",
      status: finalSub?.status ?? "active",
      expires_at: finalSub?.expires_at ?? null,
    });
  } catch (error) {
    console.error("Failed to complete telegram link:", error);
    return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
  }
}
