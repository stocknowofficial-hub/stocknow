import { NextResponse } from "next/server";
import { cookies } from "next/headers";
import { verifyAdminCookie, COOKIE_NAME } from "@/lib/admin-auth";

function getDB() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    if (ctx?.env?.DB) return ctx.env.DB as import("@cloudflare/workers-types").D1Database;
  } catch {}
  return null;
}

export async function PUT(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  console.log("[Admin PUT] token present:", !!token);
  if (!(await verifyAdminCookie(token))) {
    console.error("[Admin PUT] Unauthorized - token mismatch or missing");
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;
  const { plan, status, expires_at } = await request.json();

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB error" }, { status: 500 });

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
    .bind(id, plan, status, expires_at || null)
    .run();

  return NextResponse.json({ ok: true });
}

export async function DELETE(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  if (!(await verifyAdminCookie(token))) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;
  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB error" }, { status: 500 });

  // 관련 데이터 순서대로 삭제 (FK 제약)
  await db.batch([
    db.prepare("DELETE FROM subscriptions WHERE user_id = ?").bind(id),
    db.prepare("DELETE FROM referrals WHERE referrer_id = ? OR referee_id = ?").bind(id, id),
    db.prepare("DELETE FROM payments WHERE user_id = ?").bind(id),
    db.prepare("DELETE FROM sessions WHERE userId = ?").bind(id),
    db.prepare("DELETE FROM accounts WHERE userId = ?").bind(id),
    db.prepare("DELETE FROM telegram_link_tokens WHERE user_id = ?").bind(id),
    db.prepare("DELETE FROM users WHERE id = ?").bind(id),
  ]);

  return NextResponse.json({ ok: true });
}
