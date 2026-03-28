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

/** GET /api/predictions — 예측 목록 조회 */
export async function GET(request: Request) {
  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const { searchParams } = new URL(request.url);
  const status = searchParams.get("status"); // 'pending' | 'completed'
  const source = searchParams.get("source"); // e.g. 'trump'
  const limit = Math.min(parseInt(searchParams.get("limit") ?? "20"), 50);
  const offset = Math.max(parseInt(searchParams.get("offset") ?? "0"), 0);

  const conditions: string[] = [];
  const bindings: (string | number)[] = [];

  if (status === "pending") conditions.push("result IS NULL");
  else if (status === "completed") conditions.push("result IS NOT NULL");

  // source는 파라미터 바인딩으로 SQL injection 방지
  if (source) {
    conditions.push("source = ?");
    bindings.push(source);
  }

  let query = "SELECT * FROM predictions";
  if (conditions.length > 0) query += " WHERE " + conditions.join(" AND ");
  query += " ORDER BY created_at DESC LIMIT ? OFFSET ?";
  bindings.push(limit, offset);

  const rows = await db.prepare(query).bind(...bindings).all();

  // 누적 적중률 계산
  const statsRow = await db
    .prepare("SELECT COUNT(*) as total, SUM(CASE WHEN result = 'hit' THEN 1 ELSE 0 END) as hits FROM predictions WHERE result IS NOT NULL")
    .first<{ total: number; hits: number }>();

  const total = statsRow?.total ?? 0;
  const hits = statsRow?.hits ?? 0;
  const hitRate = total > 0 ? Math.round((hits / total) * 100) : null;

  return NextResponse.json({
    predictions: rows.results,
    stats: { total, hits, hitRate },
  });
}

/** POST /api/predictions — worker에서 예측 카드 저장 */
export async function POST(request: Request) {
  if (!authOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const body = await request.json() as {
    source: string;
    source_desc?: string;
    source_url?: string;
    prediction: string;
    direction: string;
    target: string;
    target_code?: string;
    basis?: string;
    key_points?: string[];
    related_stocks?: { name: string; code: string; reason: string }[];
    action?: string;
    action_reason?: string;
    trade_setup?: { entry?: string; stop_loss?: string; target?: string };
    timeframe: number;
    confidence: string;
    entry_price?: number;
  };

  const { source, source_desc, source_url, prediction, direction, target, target_code, basis, key_points, related_stocks, action, action_reason, trade_setup, timeframe, confidence, entry_price } = body;

  if (!source || !prediction || !direction || !target || !timeframe || !confidence) {
    return NextResponse.json({ error: "필수 필드 누락" }, { status: 400 });
  }

  // 중복 체크 (같은 source_url에서 이미 생성된 예측이 있으면 스킵)
  if (source_url) {
    const existing = await db
      .prepare("SELECT id FROM predictions WHERE source_url = ?")
      .bind(source_url)
      .first();
    if (existing) {
      return NextResponse.json({ ok: true, skipped: true, reason: "duplicate source_url" });
    }
  }

  const now = new Date();
  const expiresAt = new Date(now.getTime() + timeframe * 24 * 60 * 60 * 1000)
    .toISOString()
    .slice(0, 19)
    .replace("T", " ");

  const id = `pred_${now.toISOString().slice(0, 10).replace(/-/g, "")}_${source}_${Date.now().toString(36)}`;

  const keyPointsJson = key_points && key_points.length > 0 ? JSON.stringify(key_points) : null;
  const relatedStocksJson = related_stocks && related_stocks.length > 0 ? JSON.stringify(related_stocks) : null;
  const tradeSetupJson = trade_setup ? JSON.stringify(trade_setup) : null;

  await db
    .prepare(
      `INSERT INTO predictions (id, source, source_desc, source_url, prediction, direction, target, target_code, basis, key_points, related_stocks, action, trade_setup, timeframe, expires_at, confidence, entry_price)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(id, source, source_desc ?? null, source_url ?? null, prediction, direction, target, target_code ?? null, basis ?? null, keyPointsJson, relatedStocksJson, action ? `${action}${action_reason ? ` · ${action_reason}` : ''}` : null, tradeSetupJson, timeframe, expiresAt, confidence, entry_price ?? null)
    .run();

  return NextResponse.json({ ok: true, id });
}
