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

interface MacroRow {
  key: string;
  value: number;
  label: string;
  prev_close: number | null;
  week_ago: number | null;
  month_ago: number | null;
  updated_at: string | null;
}

/** GET /api/macro — 매크로 지표 조회 */
export async function GET() {
  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const { results } = await db
    .prepare("SELECT * FROM macro_feed")
    .all<MacroRow>();

  const data: Record<string, MacroRow> = {};
  for (const row of results) {
    data[row.key] = row;
  }

  return NextResponse.json(data);
}

/** POST /api/macro — watcher에서 매크로 지표 저장 */
export async function POST(request: Request) {
  if (!authOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const items = await request.json() as Array<{
    key: string;
    value: number;
    label: string;
    prev_close?: number | null;
    week_ago?: number | null;
    month_ago?: number | null;
  }>;

  try {
    for (const item of items) {
      await db
        .prepare(
          `INSERT INTO macro_feed (key, value, label, prev_close, week_ago, month_ago, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(key) DO UPDATE SET
             value      = excluded.value,
             label      = excluded.label,
             prev_close = excluded.prev_close,
             week_ago   = excluded.week_ago,
             month_ago  = excluded.month_ago,
             updated_at = excluded.updated_at`
        )
        .bind(
          item.key,
          item.value,
          item.label,
          item.prev_close ?? null,
          item.week_ago ?? null,
          item.month_ago ?? null,
        )
        .run();
    }
  } catch (e) {
    console.error("[MacroAPI] DB insert error:", e);
    return NextResponse.json({ error: String(e) }, { status: 500 });
  }

  return NextResponse.json({ ok: true, saved: items.length });
}
