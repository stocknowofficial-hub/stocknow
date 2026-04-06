import { NextResponse } from "next/server";

function getDB() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    if (ctx?.env?.DB) return ctx.env.DB as import("@cloudflare/workers-types").D1Database;
  } catch {}
  return null;
}

const ETF_NAMES: Record<string, string> = {
  "069500": "KODEX 200",
  "379800": "KODEX S&P500",
  "133690": "TIGER 나스닥100",
  "261220": "KODEX WTI원유",
  "091160": "KODEX 반도체",
  "228800": "KODEX 금선물",
  "102110": "TIGER 200",
  "308620": "KODEX 차이나",
  "195930": "TIGER 유럽",
  "360750": "TIGER 미국S&P500",
};

function getTargetName(target: string | null, code: string | null): string {
  if (code && ETF_NAMES[code]) return ETF_NAMES[code];
  if (target && ETF_NAMES[target]) return ETF_NAMES[target];
  if (target && !/^\d+$/.test(target)) return target;
  return target || code || "알 수 없음";
}

/** GET /api/consensus-data — watcher용 이번 주 컨센서스 집계 데이터 */
export async function GET() {
  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const [targetRows, trumpRows] = await Promise.all([
    db
      .prepare(
        `SELECT target, target_code, direction, COUNT(*) as cnt
         FROM predictions
         WHERE created_at >= datetime('now', '-7 days') AND source != 'trump'
         GROUP BY target, direction`
      )
      .all<{ target: string; target_code: string | null; direction: string; cnt: number }>(),
    db
      .prepare(
        `SELECT prediction FROM predictions
         WHERE source = 'trump' AND created_at >= datetime('now', '-7 days')
         ORDER BY created_at DESC LIMIT 5`
      )
      .all<{ prediction: string }>(),
  ]);

  const targetMap = new Map<string, { name: string; up: number; down: number; sideways: number }>();
  for (const row of targetRows.results) {
    const name = getTargetName(row.target, row.target_code);
    const existing = targetMap.get(name) ?? { name, up: 0, down: 0, sideways: 0 };
    if (row.direction === "up") existing.up += row.cnt;
    else if (row.direction === "down") existing.down += row.cnt;
    else existing.sideways += row.cnt;
    targetMap.set(name, existing);
  }

  const sorted = [...targetMap.values()].sort((a, b) => (b.up + b.down + b.sideways) - (a.up + a.down + a.sideways));
  const bullish = sorted.filter((t) => t.up > t.down && t.up > t.sideways).slice(0, 5);
  const bearish = sorted.filter((t) => t.down > t.up).slice(0, 3);

  return NextResponse.json({
    bullish: bullish.map((t) => ({ name: t.name, count: t.up })),
    bearish: bearish.map((t) => ({ name: t.name, count: t.down })),
    trump_snippets: trumpRows.results.map((r) => r.prediction.slice(0, 100)),
  });
}
