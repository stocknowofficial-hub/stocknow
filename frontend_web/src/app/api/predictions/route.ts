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
  const limit = Math.min(parseInt(searchParams.get("limit") ?? "20"), 50);

  let query = "SELECT * FROM predictions";
  if (status === "pending") {
    query += " WHERE result IS NULL";
  } else if (status === "completed") {
    query += " WHERE result IS NOT NULL";
  }
  query += " ORDER BY created_at DESC LIMIT ?";

  const rows = await db.prepare(query).bind(limit).all();

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
    timeframe: number;
    confidence: string;
    entry_price?: number;
  };

  const { source, source_desc, source_url, prediction, direction, target, target_code, basis, key_points, timeframe, confidence, entry_price } = body;

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

  await db
    .prepare(
      `INSERT INTO predictions (id, source, source_desc, source_url, prediction, direction, target, target_code, basis, key_points, timeframe, expires_at, confidence, entry_price)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .bind(id, source, source_desc ?? null, source_url ?? null, prediction, direction, target, target_code ?? null, basis ?? null, keyPointsJson, timeframe, expiresAt, confidence, entry_price ?? null)
    .run();

  return NextResponse.json({ ok: true, id });
}
