import { NextResponse } from "next/server";

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
  const auth = request.headers.get("Authorization") ?? "";
  return auth === `Bearer ${secret}`;
}

/** GET /api/cron/expired — 만료된 유료 구독자 목록 반환 */
export async function GET(request: Request) {
  if (!authOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB error" }, { status: 500 });

  const { results } = await db
    .prepare(
      `SELECT u.id, u.name, u.telegram_id,
              s.plan, s.expires_at
       FROM subscriptions s
       JOIN users u ON u.id = s.user_id
       WHERE s.status = 'active'
         AND s.plan != 'free'
         AND s.expires_at IS NOT NULL
         AND s.expires_at < CURRENT_TIMESTAMP`
    )
    .all<{
      id: string;
      name: string | null;
      telegram_id: string | null;
      plan: string;
      expires_at: string;
    }>();

  return NextResponse.json({ users: results });
}

/** POST /api/cron/expired — 특정 유저를 만료 처리 (status → expired) */
export async function POST(request: Request) {
  if (!authOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { user_id } = await request.json();
  if (!user_id) {
    return NextResponse.json({ error: "user_id required" }, { status: 400 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB error" }, { status: 500 });

  await db
    .prepare(
      `UPDATE subscriptions SET status = 'expired', updated_at = CURRENT_TIMESTAMP
       WHERE user_id = ?`
    )
    .bind(user_id)
    .run();

  return NextResponse.json({ ok: true });
}
