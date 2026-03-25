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

interface ActivePrediction {
  id: string;
  direction: string;
  target_code: string;
  entry_price: number | null;
}

/**
 * GET /api/cron/update-prediction-prices
 * 진행중 예측들의 현재가를 네이버 금융에서 조회해 갱신
 * Cloudflare Cron Trigger: 매 2시간
 */
export async function GET(request: Request) {
  if (!authOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  // target_code 있는 진행중 예측만 조회
  const { results } = await db
    .prepare(
      `SELECT id, direction, target_code, entry_price
       FROM predictions
       WHERE result IS NULL
         AND target_code IS NOT NULL`
    )
    .all() as { results: ActivePrediction[] };

  if (results.length === 0) {
    return NextResponse.json({ ok: true, updated: 0, message: "추적 중인 예측 없음" });
  }

  let updated = 0;
  const errors: string[] = [];

  for (const pred of results) {
    try {
      // 네이버 금융에서 현재가 조회
      const price = await fetchNaverPrice(pred.target_code);
      if (!price) {
        errors.push(`${pred.target_code}: 가격 조회 실패`);
        continue;
      }

      // entry_price 없으면 지금 가격을 entry로 설정
      const entryPrice = pred.entry_price ?? price;
      const changePct = ((price - entryPrice) / entryPrice) * 100;

      await db
        .prepare(
          `UPDATE predictions
           SET current_price = ?,
               entry_price = COALESCE(entry_price, ?),
               price_change_pct = ?,
               price_updated_at = datetime('now')
           WHERE id = ?`
        )
        .bind(price, price, Math.round(changePct * 100) / 100, pred.id)
        .run();

      updated++;
    } catch (e) {
      errors.push(`${pred.id}: ${e}`);
    }
  }

  return NextResponse.json({ ok: true, updated, total: results.length, errors });
}

async function fetchNaverPrice(code: string): Promise<number | null> {
  try {
    const res = await fetch(
      `https://m.stock.naver.com/api/stock/${code}/basic`,
      { headers: { 'User-Agent': 'Mozilla/5.0' } }
    );
    if (!res.ok) return null;
    const data = await res.json() as { closePrice?: string };
    if (!data.closePrice) return null;
    return parseFloat(data.closePrice.replace(/,/g, ''));
  } catch {
    return null;
  }
}
