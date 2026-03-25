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

/** PATCH /api/predictions/[id] — 결과 업데이트 (cron에서 호출) */
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
    result: "hit" | "miss" | "partial";
    result_val?: string;
  };

  const { result, result_val } = body;
  if (!result) return NextResponse.json({ error: "result 필드 필요" }, { status: 400 });

  await db
    .prepare(
      `UPDATE predictions SET result = ?, result_val = ?, result_at = datetime('now') WHERE id = ?`
    )
    .bind(result, result_val ?? null, id)
    .run();

  return NextResponse.json({ ok: true });
}
