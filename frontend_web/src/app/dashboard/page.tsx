import Link from "next/link";
import { redirect } from "next/navigation";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { TelegramLinkButton } from "@/components/TelegramLinkButton";
import { PremiumUpgradeButton } from "@/components/PremiumUpgradeButton";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { PaymentBanner } from "@/components/PaymentBanner";
import { Suspense } from "react";

interface Subscription {
  plan: string;
  status: string;
  expires_at: string | null;
}

interface UserRow {
  telegram_id: string | null;
}

interface ReferralCount {
  count: number;
}

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);

  if (!session?.user) redirect("/auth/signin");

  const userId = session.user.id as string;

  // ── D1에서 실데이터 조회 ──────────────────────────────────────────
  let subscription: Subscription | null = null;
  let referralCount = 0;
  let telegramLinked = false;

  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    const db = ctx?.env?.DB as import("@cloudflare/workers-types").D1Database | undefined;
    if (db) {
      const [sub, referrals, userRow] = await Promise.all([
        db
          .prepare("SELECT plan, status, expires_at FROM subscriptions WHERE user_id = ?")
          .bind(userId)
          .first<Subscription>(),
        db
          .prepare("SELECT COUNT(*) as count FROM referrals WHERE referrer_id = ? AND rewarded = 1")
          .bind(userId)
          .first<ReferralCount>(),
        db
          .prepare("SELECT telegram_id FROM users WHERE id = ?")
          .bind(userId)
          .first<UserRow>(),
      ]);

      subscription = sub;
      referralCount = referrals?.count ?? 0;
      telegramLinked = !!userRow?.telegram_id;

      // auth.ts D1 upsert가 실패했을 경우 대시보드에서 보완 생성
      if (!sub) {
        await db
          .prepare(
            "INSERT OR IGNORE INTO subscriptions (user_id, plan, status, expires_at) VALUES (?, 'free', 'active', NULL)"
          )
          .bind(userId)
          .run();
        subscription = { plan: "free", status: "active", expires_at: null };
      }
    }
  } catch (e) {
    console.error("[Dashboard] D1 fetch failed:", e);
  }

  // ── 표시용 값 계산 ────────────────────────────────────────────────
  const plan = subscription?.plan ?? "free";

  const planLabel: Record<string, string> = {
    free: "FREE PLAN",
    trial: "7일 무료 체험",
    standard: "STANDARD",
    standard_kr: "STANDARD KR",
    standard_us: "STANDARD US",
    premium: "PREMIUM",
    pro: "PRO PLAN",
  };
  const planDisplay = planLabel[plan] ?? plan.toUpperCase();
  const isPaid = plan !== "free" && plan !== "trial";

  // expires_at = NULL → 무제한 (free plan은 만료 없음)
  const expiresDisplay = subscription?.expires_at
    ? new Date(subscription.expires_at).toLocaleDateString("ko-KR", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "무제한";

  // 초대 코드: userId의 숫자 파트 뒤 8자리로 생성 (예: SN-1234-5678)
  const numericPart = userId.replace(/^[^_]+_/, "").replace(/\D/g, "");
  const code = numericPart.slice(-8).padStart(8, "0");
  const referralCode = `SN-${code.slice(0, 4)}-${code.slice(4)}`;

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white">
      <div className="flex h-screen overflow-hidden">
        <DashboardSidebar user={session.user} />

        {/* Main */}
        <main className="flex-1 overflow-y-auto p-8 lg:p-12">
          <Suspense fallback={null}>
            <PaymentBanner />
          </Suspense>
          <header className="mb-10 flex items-center justify-between">
            <div>
              <h2 className="text-3xl font-bold mb-1">
                안녕하세요, {session.user.name?.split(" ")[0] || "반가워요"}! 👋
              </h2>
              <p className="text-gray-500 text-sm">오늘은 국내 거래소 고래 수급이 활발합니다.</p>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span
                className={`px-3 py-1.5 rounded-full border font-medium flex items-center gap-2 ${
                  !isPaid
                    ? "bg-white/5 text-gray-400 border-white/10"
                    : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                }`}
              >
                <span
                  className={`w-2 h-2 rounded-full ${
                    !isPaid ? "bg-gray-500" : "bg-emerald-500 animate-pulse"
                  }`}
                />
                {planDisplay}
              </span>
            </div>
          </header>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Subscription Card */}
            <div className="lg:col-span-2 p-8 rounded-3xl bg-gradient-to-br from-purple-600/20 to-blue-600/20 border border-white/10 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-8 text-8xl opacity-10 blur-sm pointer-events-none group-hover:scale-110 transition-transform duration-700">
                👑
              </div>
              <h3 className="text-xl font-bold mb-6">내 구독 정보</h3>
              <div className="flex items-end justify-between">
                <div>
                  <div className="text-4xl font-black mb-2 tracking-tight">{planDisplay}</div>
                  <p className="text-gray-400 text-sm mb-6">
                    {plan === "trial"
                      ? `7일 무료 체험 중입니다. ${expiresDisplay}에 체험이 종료되며, 이후 결제하시면 VIP 채널을 계속 이용하실 수 있습니다.`
                      : isPaid
                      ? "구독 중입니다. 모든 기능을 사용할 수 있습니다."
                      : "무료 플랜을 이용 중입니다. 텔레그램을 연동하여 실시간 알림을 받아보세요."}
                  </p>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <TelegramLinkButton isLinked={telegramLinked} />
                    {!isPaid && <PremiumUpgradeButton />}
                  </div>
                </div>
                <div className="text-right hidden sm:block">
                  <div className="text-gray-500 text-xs mb-1">
                    {subscription?.expires_at ? "만료 예정일" : "플랜 유효 기간"}
                  </div>
                  <div className="text-lg font-semibold">{expiresDisplay}</div>
                </div>
              </div>
            </div>

            {/* Referral Card */}
            <div className="p-8 rounded-3xl bg-white/[0.03] border border-white/10 flex flex-col">
              <h3 className="text-xl font-bold mb-4">친구 초대 혜택</h3>
              <p className="text-gray-400 text-sm mb-8 leading-relaxed">
                친구 한 명을 초대할 때마다 <br />
                <span className="text-white font-semibold underline decoration-purple-500 underline-offset-4">
                  구독 기간이 1개월 연장
                </span>
                됩니다!
              </p>

              <div className="space-y-4 mb-4">
                <div className="p-4 rounded-2xl bg-black/40 border border-white/5 space-y-2">
                  <div className="text-[10px] text-gray-500 uppercase font-bold tracking-widest">
                    내 초대 코드
                  </div>
                  <div className="flex items-center justify-between font-mono text-purple-400">
                    <span>{referralCode}</span>
                    <button
                      onClick={undefined}
                      className="text-xs px-2 py-1 bg-white/5 rounded-lg hover:bg-white/10 text-white transition-colors"
                    >
                      복사
                    </button>
                  </div>
                </div>
              </div>

              <div className="mt-auto pt-4 border-t border-white/5 flex items-center justify-between text-sm">
                <span className="text-gray-500">누적 보상</span>
                <span className="font-bold">{referralCount} 개월</span>
              </div>
            </div>

            {/* Live Feed Card (Mockup – 실제 데이터 파이프라인 연결 전) */}
            <div className="lg:col-span-3 p-8 rounded-3xl bg-white/[0.03] border border-white/10">
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-xl font-bold">실시간 고래 수급 피드</h3>
                <Link href="#" className="text-sm text-purple-400 hover:underline">
                  자세히 보기
                </Link>
              </div>
              <div className="space-y-4">
                {[
                  {
                    time: "10분 전",
                    title: "비트코인(BTC) 대량 입금 감지",
                    detail: "익명 지갑 → Upbit (120 BTC)",
                    bg: "bg-blue-400/10",
                  },
                  {
                    time: "25분 전",
                    title: "이더리움(ETH) 고래 매집",
                    detail: "Binance → 익명 지갑 (5,000 ETH)",
                    bg: "bg-purple-400/10",
                  },
                  {
                    time: "1시간 전",
                    title: "리플(XRP) 급격한 수급 변동",
                    detail: "전일 대비 대량 거래 3배 증가",
                    bg: "bg-emerald-400/10",
                  },
                ].map((item, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-4 p-4 rounded-2xl hover:bg-white/[0.02] transition-colors border border-transparent hover:border-white/5"
                  >
                    <div
                      className={`w-12 h-12 rounded-xl ${item.bg} flex items-center justify-center text-xl`}
                    >
                      👁️
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-0.5">
                        <span className="font-semibold text-white">{item.title}</span>
                        <span className="text-xs text-gray-600">{item.time}</span>
                      </div>
                      <div className="text-sm text-gray-500">{item.detail}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
