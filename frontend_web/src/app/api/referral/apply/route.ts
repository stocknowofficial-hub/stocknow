import { NextResponse } from "next/server";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";

function getDB() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    if (ctx?.env?.DB) return ctx.env.DB as import("@cloudflare/workers-types").D1Database;
  } catch {}
  return null;
}

/**
 * POST /api/referral/apply
 * Body: { code: "SN-XXXX-YYYY" }
 *
 * 1. 코드로 추천인 ID 조회 (id_social LIKE '%XXXXYYYY')
 * 2. 자기 자신 / 이미 등록된 경우 거부
 * 3. referee referred_by 저장
 * 4. referrals 테이블에 행 삽입 (rewarded=1로 즉시 적용)
 * 5. referee 구독 1개월 연장 (보너스)
 * 6. referrer 구독 1개월 연장 (보상)
 */
export async function POST(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const refereeId = session.user.id as string;

  let body: { code?: string };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid body" }, { status: 400 });
  }

  const raw = (body.code ?? "").trim().toUpperCase();
  // 형식 검증: SN-XXXX-YYYY
  if (!/^SN-[0-9]{4}-[0-9]{4}$/.test(raw)) {
    return NextResponse.json({ error: "올바른 초대 코드 형식이 아닙니다. (SN-XXXX-XXXX)" }, { status: 400 });
  }

  // 숫자 8자리 추출
  const digits = raw.replace(/\D/g, ""); // "XXXXYYYY"

  const db = getDB();
  if (!db) return NextResponse.json({ error: "DB error" }, { status: 500 });

  // 이미 referred_by가 등록된 경우 차단
  const refereRow = await db
    .prepare("SELECT referred_by FROM users WHERE id = ?")
    .bind(refereeId)
    .first<{ referred_by: string | null }>();

  if (refereRow?.referred_by) {
    return NextResponse.json({ error: "이미 추천인 코드가 등록되어 있습니다." }, { status: 409 });
  }

  // 추천인 조회: id_social 끝 8자리 매칭
  // padStart로 인한 앞자리 0 제거 후 LIKE 검색 (짧은 ID 대응)
  const digitsTrimmed = digits.replace(/^0+/, "") || "0";
  const rows = await db
    .prepare("SELECT id FROM users WHERE id_social LIKE ? AND id_social IS NOT NULL LIMIT 2")
    .bind(`%${digitsTrimmed}`)
    .all<{ id: string }>();

  if (!rows.results || rows.results.length === 0) {
    return NextResponse.json({ error: "존재하지 않는 초대 코드입니다." }, { status: 404 });
  }
  if (rows.results.length > 1) {
    return NextResponse.json({ error: "초대 코드를 특정할 수 없습니다. 고객센터에 문의해주세요." }, { status: 409 });
  }

  const referrerId = rows.results[0].id;

  if (referrerId === refereeId) {
    return NextResponse.json({ error: "본인의 초대 코드는 사용할 수 없습니다." }, { status: 400 });
  }

  // 이미 같은 추천 관계가 있는지 확인 (중복 방지)
  const dup = await db
    .prepare("SELECT id FROM referrals WHERE referrer_id = ? AND referee_id = ?")
    .bind(referrerId, refereeId)
    .first();

  if (dup) {
    return NextResponse.json({ error: "이미 처리된 초대 코드입니다." }, { status: 409 });
  }

  // 추천인 최대 20명 cap 확인
  const referrerCount = await db
    .prepare("SELECT COUNT(*) as cnt FROM referrals WHERE referrer_id = ? AND rewarded = 1")
    .bind(referrerId)
    .first<{ cnt: number }>();

  if ((referrerCount?.cnt ?? 0) >= 20) {
    return NextResponse.json({ error: "추천인의 초대 한도(20명)가 초과되었습니다." }, { status: 409 });
  }

  // ── DB 업데이트 ──────────────────────────────────────
  await db
    .prepare("UPDATE users SET referred_by = ? WHERE id = ?")
    .bind(referrerId, refereeId)
    .run();

  await db
    .prepare(
      "INSERT INTO referrals (referrer_id, referee_id, rewarded) VALUES (?, ?, 1)"
    )
    .bind(referrerId, refereeId)
    .run();

  // referrer 구독 +7일 연장 (추천인 보상)
  await db
    .prepare(
      `UPDATE subscriptions
       SET expires_at = COALESCE(datetime(expires_at, '+7 days'), datetime('now', '+7 days')),
           updated_at = CURRENT_TIMESTAMP
       WHERE user_id = ?`
    )
    .bind(referrerId)
    .run();

  return NextResponse.json({ ok: true });
}
