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

interface WhaleFeedRow {
  market: string;
  program_items: string | null;
  foreign_items: string | null;
  volume_items: string | null;
  updated_at: string | null;
}

/** GET /api/whale-feed — 대시보드에서 읽기 (인증 불필요) */
export async function GET() {
  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const row = await db
    .prepare("SELECT * FROM whale_feed WHERE market = 'KR'")
    .first<WhaleFeedRow>();

  if (!row) {
    return NextResponse.json({ sections: null, updated_at: null });
  }

  return NextResponse.json({
    sections: {
      program: JSON.parse(row.program_items ?? "[]"),
      foreign: JSON.parse(row.foreign_items ?? "[]"),
      volume: JSON.parse(row.volume_items ?? "[]"),
    },
    updated_at: row.updated_at,
  });
}

/** POST /api/whale-feed — watcher에서 업데이트 (X-Secret-Key 인증) */
export async function POST(request: Request) {
  if (!authOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const body = await request.json() as {
    market: string;
    program_items: object[];
    foreign_items: object[];
    volume_items: object[];
  };

  const { market, program_items, foreign_items, volume_items } = body;
  if (!market) return NextResponse.json({ error: "market required" }, { status: 400 });

  await db
    .prepare(
      `INSERT INTO whale_feed (market, program_items, foreign_items, volume_items, updated_at)
       VALUES (?, ?, ?, ?, datetime('now'))
       ON CONFLICT(market) DO UPDATE SET
         program_items = excluded.program_items,
         foreign_items = excluded.foreign_items,
         volume_items  = excluded.volume_items,
         updated_at    = excluded.updated_at`
    )
    .bind(
      market,
      JSON.stringify(program_items ?? []),
      JSON.stringify(foreign_items ?? []),
      JSON.stringify(volume_items ?? []),
    )
    .run();

  return NextResponse.json({ ok: true });
}
