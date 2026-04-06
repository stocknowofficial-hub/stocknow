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

/** PATCH /api/predictions/[id] — 가격 및 결과 업데이트 (watcher에서 호출) */
export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  if (!authOk(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB unavailable" }, { status: 503 });

  const body = await request.json() as {
    result?: "hit" | "miss" | "partial";
    result_val?: string;
    current_price?: number;
    entry_price?: number;
    price_change_pct?: number;
    peak_change_pct?: number;
    peak_at?: string;
    hit_change_pct?: number;
    hit_at?: string;
  };

  const { result, result_val, current_price, entry_price, price_change_pct,
          peak_change_pct, peak_at, hit_change_pct, hit_at } = body;

  const setClauses: string[] = [];
  const bindings: (string | number | null)[] = [];

  if (current_price != null) { setClauses.push("current_price = ?"); bindings.push(current_price); }
  if (entry_price != null)   { setClauses.push("entry_price = COALESCE(entry_price, ?)"); bindings.push(entry_price); }
  if (price_change_pct != null) { setClauses.push("price_change_pct = ?"); bindings.push(price_change_pct); }
  if (current_price != null) { setClauses.push("price_updated_at = datetime('now')"); }
  // Peak: 항상 갱신 (watcher에서 이미 최고값 비교 후 전달)
  if (peak_change_pct != null) { setClauses.push("peak_change_pct = ?"); bindings.push(peak_change_pct); }
  if (peak_at != null)         { setClauses.push("peak_at = ?"); bindings.push(peak_at); }
  // Hit 스냅샷: hit_change_pct/hit_at는 최초 1회만 저장 (COALESCE로 덮어쓰기 방지)
  if (hit_change_pct != null) { setClauses.push("hit_change_pct = COALESCE(hit_change_pct, ?)"); bindings.push(hit_change_pct); }
  if (hit_at != null)         { setClauses.push("hit_at = COALESCE(hit_at, ?)"); bindings.push(hit_at); }
  if (result) {
    setClauses.push("result = ?");
    bindings.push(result);
    setClauses.push("result_val = ?");
    bindings.push(result_val ?? null);
    setClauses.push("result_at = datetime('now')");
  }

  if (setClauses.length === 0) {
    return NextResponse.json({ error: "업데이트할 필드 없음" }, { status: 400 });
  }

  bindings.push(id);
  await db
    .prepare(`UPDATE predictions SET ${setClauses.join(", ")} WHERE id = ?`)
    .bind(...bindings)
    .run();

  return NextResponse.json({ ok: true });
}
