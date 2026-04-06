import { NextResponse } from "next/server";

function getDB() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    if (ctx?.env?.DB) return ctx.env.DB as import("@cloudflare/workers-types").D1Database;
  } catch {}
  return null;
}

/** GET /api/wallstreet — 최신 월가 컨센서스 목록 */
export async function GET() {
  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const rows = await db
    .prepare(
      `SELECT ticker, name, recommendation, target_price, current_price, analyst_count, upside_pct, updated_at
       FROM wallstreet_consensus
       ORDER BY updated_at DESC`
    )
    .all<{
      ticker: string;
      name: string;
      recommendation: string;
      target_price: number;
      current_price: number;
      analyst_count: number;
      upside_pct: number;
      updated_at: string;
    }>();

  return NextResponse.json({ items: rows.results });
}

/** POST /api/wallstreet — watcher가 월가 데이터 저장 */
export async function POST(request: Request) {
  const secret = request.headers.get("X-Secret-Key");
  if (!process.env.WHALE_SECRET || secret !== process.env.WHALE_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const items = await request.json() as Array<{
    ticker: string;
    name: string;
    recommendation: string;
    target_price: number | null;
    current_price: number | null;
    analyst_count: number;
    upside_pct: number | null;
  }>;

  for (const item of items) {
    await db
      .prepare(
        `INSERT INTO wallstreet_consensus (ticker, name, recommendation, target_price, current_price, analyst_count, upside_pct, updated_at)
         VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
         ON CONFLICT(ticker) DO UPDATE SET
           name=excluded.name, recommendation=excluded.recommendation,
           target_price=excluded.target_price, current_price=excluded.current_price,
           analyst_count=excluded.analyst_count, upside_pct=excluded.upside_pct,
           updated_at=excluded.updated_at`
      )
      .bind(item.ticker, item.name, item.recommendation, item.target_price, item.current_price, item.analyst_count, item.upside_pct)
      .run();
  }

  return NextResponse.json({ ok: true, saved: items.length });
}
