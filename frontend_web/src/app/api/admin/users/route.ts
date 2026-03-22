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

export async function GET() {
  const cookieStore = await cookies();
  const token = cookieStore.get(COOKIE_NAME)?.value;
  if (!(await verifyAdminCookie(token))) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB error" }, { status: 500 });

  const { results } = await db
    .prepare(
      `SELECT u.id, u.name, u.email, u.id_type, u.telegram_id, u.telegram_name,
              u.created_at,
              s.plan, s.status, s.expires_at
       FROM users u
       LEFT JOIN subscriptions s ON s.user_id = u.id
       ORDER BY u.created_at DESC
       LIMIT 200`
    )
    .all();

  return NextResponse.json({ users: results });
}
