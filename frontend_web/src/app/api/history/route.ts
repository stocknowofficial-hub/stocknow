import { NextRequest } from 'next/server';

const PAGE_SIZE = 5;

const PENDING_ORDER = `
  CASE confidence WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END ASC,
  CASE
    WHEN direction = 'up' AND price_change_pct > 0 THEN 0
    WHEN direction = 'down' AND price_change_pct < 0 THEN 0
    ELSE 1
  END ASC,
  expires_at ASC
`;

export async function GET(request: NextRequest) {
  try {
    const { getCloudflareContext } = require('@opennextjs/cloudflare');
    const db = getCloudflareContext()?.env?.DB;
    if (!db) return Response.json({ error: 'no db' }, { status: 500 });

    const section = request.nextUrl.searchParams.get('section') ?? 'pending'; // hit | miss | pending
    const offset = parseInt(request.nextUrl.searchParams.get('offset') ?? '0');
    const limit = Math.min(parseInt(request.nextUrl.searchParams.get('limit') ?? String(PAGE_SIZE)), 20);

    const where =
      section === 'hit' ? `result = 'hit'` :
      section === 'miss' ? `result = 'miss'` :
      `result IS NULL`;

    const orderBy =
      section === 'pending'
        ? PENDING_ORDER
        : section === 'hit'
        ? `ABS(COALESCE(peak_change_pct, hit_change_pct, price_change_pct, 0)) DESC`
        : `created_at DESC`;

    const rows = await db
      .prepare(
        `SELECT id, source, source_desc, prediction, direction, target, target_code, result,
                entry_price, current_price, price_change_pct, peak_change_pct, peak_at, hit_change_pct, hit_at,
                trade_setup, created_at, expires_at, confidence, basis
         FROM predictions
         WHERE ${where}
         ORDER BY ${orderBy}
         LIMIT ? OFFSET ?`
      )
      .bind(limit, offset)
      .all();

    const preds = rows.results as Array<{ target_code: string | null }>;

    // 이 배치에 포함된 종목의 wallstreet_consensus 조회
    const tickers = [...new Set(
      preds.map((p) => p.target_code)
           .filter((c): c is string => !!c && (/^[A-Za-z]{1,5}$/.test(c) || /^\d{6}$/.test(c)))
    )];

    let wsMap: Record<string, unknown> = {};
    if (tickers.length > 0) {
      const ph = tickers.map(() => '?').join(',');
      const wsRows = await db
        .prepare(`SELECT ticker, recommendation, target_price, upside_pct, analyst_count FROM wallstreet_consensus WHERE ticker IN (${ph})`)
        .bind(...tickers)
        .all();
      wsMap = Object.fromEntries((wsRows.results as Array<{ ticker: string }>).map((r) => [r.ticker, r]));
    }

    return Response.json({ predictions: rows.results, wsMap });
  } catch (e) {
    return Response.json({ error: String(e) }, { status: 500 });
  }
}
