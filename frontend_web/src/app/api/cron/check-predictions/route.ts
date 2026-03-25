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

interface PredictionRow {
  id: string;
  prediction: string;
  direction: string;
  target: string;
  target_code: string | null;
  created_at: string;
  expires_at: string;
  timeframe: number;
}

/**
 * GET /api/cron/check-predictions
 * 만료된 예측들의 결과를 체크.
 *
 * target_code가 있는 경우: 자동 판정 (추후 KIS API 연동)
 * target_code가 없는 경우: 'pending_review' 상태로 남겨둠 (수동 입력)
 *
 * Cloudflare Cron Trigger: 매일 09:05 KST (00:05 UTC)
 */
export async function GET(request: Request) {
  if (!authOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  // 오늘 만료된 예측 조회 (result가 아직 없는 것)
  const { results: expired } = await db
    .prepare(
      `SELECT id, prediction, direction, target, target_code, created_at, expires_at, timeframe
       FROM predictions
       WHERE expires_at <= datetime('now')
         AND result IS NULL`
    )
    .all<PredictionRow>();

  if (expired.length === 0) {
    return NextResponse.json({ ok: true, checked: 0, message: "만료된 예측 없음" });
  }

  let autoChecked = 0;
  let pendingReview = 0;

  for (const pred of expired) {
    if (pred.target_code) {
      // TODO: KIS API로 예측 시점 대비 현재가 변화율 조회 후 자동 판정
      // 현재는 'pending_review'로 표시 (수동 입력 대기)
      // 추후 구현: fetch price change → compare direction → set hit/miss
      await db
        .prepare(`UPDATE predictions SET result = 'pending_review', result_at = datetime('now') WHERE id = ?`)
        .bind(pred.id)
        .run();
      pendingReview++;
    } else {
      // target_code 없는 섹터/거시 예측 → 수동 검토 필요
      await db
        .prepare(`UPDATE predictions SET result = 'pending_review', result_at = datetime('now') WHERE id = ?`)
        .bind(pred.id)
        .run();
      pendingReview++;
    }
  }

  return NextResponse.json({
    ok: true,
    checked: expired.length,
    auto: autoChecked,
    pendingReview,
  });
}
