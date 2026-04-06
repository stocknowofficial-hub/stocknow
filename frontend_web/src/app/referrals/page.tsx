import { redirect } from "next/navigation";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { CopyButton } from "@/components/CopyButton";
import { MobileNav } from "@/components/MobileNav";

interface ReferralRow {
  rewarded: number;
  created_at: string;
  referee_name: string | null;
}

interface ReferrerRow {
  name: string | null;
}

interface TelegramRow {
  telegram_id: string | null;
}

export default async function ReferralsPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user) redirect("/auth/signin");

  const userId = session.user.id as string;
  const provider = userId.split("_")[0];
  let referrals: ReferralRow[] = [];
  let referrerName: string | null = null;
  let totalRewarded = 0;
  let telegramId: string | null = null;

  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    const db = ctx?.env?.DB as import("@cloudflare/workers-types").D1Database | undefined;
    if (db) {
      const [referralRows, referrerRow, tgRow] = await Promise.all([
        db
          .prepare(
            `SELECT r.rewarded, r.created_at, u.name AS referee_name
             FROM referrals r
             LEFT JOIN users u ON u.id = r.referee_id
             WHERE r.referrer_id = ?
             ORDER BY r.created_at DESC`
          )
          .bind(userId)
          .all<ReferralRow>(),
        db
          .prepare(
            `SELECT ref.name FROM users me
             LEFT JOIN users ref ON ref.id = me.referred_by
             WHERE me.id = ?`
          )
          .bind(userId)
          .first<ReferrerRow>(),
        db
          .prepare("SELECT telegram_id FROM users WHERE id = ?")
          .bind(userId)
          .first<TelegramRow>(),
      ]);

      referrals = referralRows.results ?? [];
      referrerName = referrerRow?.name ?? null;
      totalRewarded = referrals.filter((r) => r.rewarded).length;
      telegramId = tgRow?.telegram_id ?? null;
    }
  } catch (e) {
    console.error("[Referrals] D1 fetch failed:", e);
  }

  // 초대 코드: userId 숫자 파트로 생성
  const numericPart = userId.replace(/^[^_]+_/, "").replace(/\D/g, "");
  const code = numericPart.slice(-8).padStart(8, "0");
  const referralCode = `SN-${code.slice(0, 4)}-${code.slice(4)}`;

  // 텔레그램 봇 초대 링크 (telegram_id가 있으면 봇 ref 링크도 제공)
  const botUsername = process.env.TELEGRAM_BOT_USERNAME ?? "Stock_Now_Bot";
  const botRefLink = telegramId
    ? `https://t.me/${botUsername}?start=ref_${telegramId}`
    : null;

  const MAX_REFERRALS = 20;
  const rewardedCount = referrals.filter((r) => r.rewarded).length;

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white">
      <div className="flex">
        <DashboardSidebar user={session.user} provider={provider} />

        <main className="flex-1">
          <div className="px-4 pt-6 pb-28 lg:px-12 lg:pt-10 lg:pb-12 max-w-2xl mx-auto">
            <header className="mb-6">
              <h2 className="text-2xl lg:text-3xl font-bold mb-1">초대 혜택</h2>
              <p className="text-gray-500 text-sm">
                친구 1명 초대 시 <span className="text-white">+7일</span> 연장 · 최대 20명까지 적립 가능
              </p>
            </header>

            <div className="space-y-4">
              {/* 초대 링크 카드 */}
              <div className="p-6 lg:p-8 rounded-2xl lg:rounded-3xl bg-gradient-to-br from-purple-600/20 to-blue-600/20 border border-white/10">
                <h3 className="text-base font-bold mb-4">내 초대 링크</h3>
                <div className="space-y-3">
                  <div className="p-3 rounded-xl bg-black/40 border border-white/5">
                    <div className="text-[10px] text-gray-500 uppercase font-bold tracking-widest mb-2">
                      초대 코드
                    </div>
                    <div className="flex items-center justify-between font-mono text-purple-400">
                      <span className="text-sm">{referralCode}</span>
                      <CopyButton text={referralCode} label="복사" />
                    </div>
                  </div>

                  {botRefLink && (
                    <div className="p-3 rounded-xl bg-black/40 border border-white/5">
                      <div className="text-[10px] text-gray-500 uppercase font-bold tracking-widest mb-2">
                        텔레그램 초대 링크
                      </div>
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-xs text-blue-400 truncate">{botRefLink}</span>
                        <CopyButton text={botRefLink} label="복사" />
                      </div>
                    </div>
                  )}

                  {!botRefLink && (
                    <p className="text-xs text-gray-500">
                      텔레그램 계정을 연동하면 봇 초대 링크도 사용할 수 있습니다.
                    </p>
                  )}
                </div>
              </div>

              {/* 보상 현황 카드 */}
              <div className="p-6 lg:p-8 rounded-2xl lg:rounded-3xl bg-white/[0.03] border border-white/10">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-base font-bold">보상 현황</h3>
                  <div className="text-right">
                    <span className="text-xl font-black text-purple-400">+{rewardedCount * 7}일</span>
                    <div className="text-[10px] text-gray-600 mt-0.5">{rewardedCount} / {MAX_REFERRALS}명</div>
                  </div>
                </div>

                {referrerName && (
                  <div className="mb-3 px-3 py-2.5 rounded-xl bg-white/5 text-sm text-gray-400">
                    <span className="text-gray-500">나를 초대한 분: </span>
                    <span className="text-white font-medium">{referrerName}</span>
                  </div>
                )}

                {referrals.length === 0 ? (
                  <div className="text-center py-10 text-gray-600">
                    <div className="text-4xl mb-3">🎁</div>
                    <p className="text-sm">아직 초대한 친구가 없습니다.</p>
                    <p className="text-xs mt-1">초대 링크를 공유해보세요!</p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {referrals.map((r, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between p-3 rounded-xl bg-black/30 border border-white/5"
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-gray-700 to-gray-600 flex items-center justify-center text-xs font-bold shrink-0">
                            {(r.referee_name ?? "?")[0].toUpperCase()}
                          </div>
                          <div>
                            <div className="text-sm font-medium">{r.referee_name ?? "알 수 없음"}</div>
                            <div className="text-xs text-gray-500">
                              {new Date(r.created_at).toLocaleDateString("ko-KR")}
                            </div>
                          </div>
                        </div>
                        <span
                          className={`text-xs px-2.5 py-1 rounded-full font-medium shrink-0 ${
                            r.rewarded
                              ? "bg-emerald-500/20 text-emerald-400"
                              : "bg-white/5 text-gray-500"
                          }`}
                        >
                          {r.rewarded ? "보상 완료" : "대기 중"}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </main>
      </div>
      <MobileNav />
    </div>
  );
}
