import { NextRequest } from 'next/server';

const PAGE_SIZE = 5;

export async function GET(request: NextRequest) {
  try {
    const { getCloudflareContext } = require('@opennextjs/cloudflare');
    const db = getCloudflareContext()?.env?.DB;
    if (!db) return Response.json({ error: 'no db' }, { status: 500 });

    const offset = parseInt(request.nextUrl.searchParams.get('offset') ?? '0');
    const limit = Math.min(parseInt(request.nextUrl.searchParams.get('limit') ?? String(PAGE_SIZE)), 20);

    const rows = await db
      .prepare(
        `SELECT id, source, source_desc, source_url, prediction, direction, target, target_code,
                confidence, created_at, key_points, related_stocks, action, trade_setup,
                price_change_pct, expires_at
         FROM predictions
         WHERE created_at >= datetime('now', '-7 days') AND source != 'trump'
         ORDER BY created_at DESC
         LIMIT ? OFFSET ?`
      )
      .bind(limit, offset)
      .all();

    return Response.json({ reports: rows.results });
  } catch (e) {
    return Response.json({ error: String(e) }, { status: 500 });
  }
}
