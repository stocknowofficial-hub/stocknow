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
  const secret = process.env.WHALE_SECRET;
  if (!secret) return false;
  return request.headers.get("X-Secret-Key") === secret;
}

function getWeekKey(): string {
  const now = new Date();
  const jan4 = new Date(now.getFullYear(), 0, 4);
  const startOfWeek1 = new Date(jan4);
  startOfWeek1.setDate(jan4.getDate() - ((jan4.getDay() + 6) % 7));
  const monday = new Date(now);
  monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));
  const weekNo = Math.round((monday.getTime() - startOfWeek1.getTime()) / (7 * 86400000)) + 1;
  return `${now.getFullYear()}-W${String(weekNo).padStart(2, "0")}`;
}

/** GET /api/consensus-summary — 최신 주간 AI 요약 조회 */
export async function GET() {
  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  try {
    const row = await db
      .prepare("SELECT * FROM weekly_summary ORDER BY updated_at DESC LIMIT 1")
      .first<{ week_key: string; title: string; body: string; signal: string; updated_at: string }>();
    return NextResponse.json(row ?? null);
  } catch (e) {
    console.error("[ConsensusSummary] GET error:", e);
    return NextResponse.json(null);
  }
}

/** POST /api/consensus-summary — watcher가 생성한 AI 요약을 DB에 저장 */
export async function POST(request: Request) {
  if (!authOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const { title, body, signal } = await request.json() as {
    title: string;
    body: string;
    signal: string;
  };

  if (!title || !body || !signal) {
    return NextResponse.json({ error: "title, body, signal required" }, { status: 400 });
  }

  const weekKey = getWeekKey();
  try {
    await db
      .prepare(
        `INSERT INTO weekly_summary (week_key, title, body, signal, updated_at)
         VALUES (?, ?, ?, ?, datetime('now'))
         ON CONFLICT(week_key) DO UPDATE SET
           title = excluded.title,
           body = excluded.body,
           signal = excluded.signal,
           updated_at = excluded.updated_at`
      )
      .bind(weekKey, title, body, signal)
      .run();
  } catch (e) {
    console.error("[ConsensusSummary] DB error:", e);
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }

  return NextResponse.json({ ok: true, week_key: weekKey });
}
