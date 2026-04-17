import { redirect } from "next/navigation";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { TelegramLinkButton } from "@/components/TelegramLinkButton";
import { MobileNav } from "@/components/MobileNav";
import { PremiumUpgradeButton } from "@/components/PremiumUpgradeButton";
import { DashboardSidebar } from "@/components/DashboardSidebar";
import { PaymentBanner } from "@/components/PaymentBanner";
import { WhaleFeedPanel, KR_TABS, US_TABS, type Sections } from "@/components/WhaleFeedPanel";
import { CopyButton } from "@/components/CopyButton";
import { Suspense } from "react";
import Link from "next/link";
import OnboardingTourLoader from "@/components/OnboardingTourLoader";

const CURRENT_VERSION = "v1.1.0";

function formatKST(utcString: string | null) {
  if (!utcString) return null;
  try {
    const d = new Date(utcString + 'Z');
    d.setHours(d.getHours() + 9);
    const YY = String(d.getUTCFullYear()).slice(2);
    const MM = String(d.getUTCMonth() + 1).padStart(2, '0');
    const DD = String(d.getUTCDate()).padStart(2, '0');
    const hh = String(d.getUTCHours()).padStart(2, '0');
    const mm = String(d.getUTCMinutes()).padStart(2, '0');
    const ss = String(d.getUTCSeconds()).padStart(2, '0');
    return `${YY}/${MM}/${DD} ${hh}:${mm}:${ss}`;
  } catch {
    return null;
  }
}

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

export default async function DashboardPage({
  searchParams,
}: {
  searchParams: Promise<{ upgrade?: string }>;
}) {
  const params = await searchParams;
  const showUpgradeBanner = params.upgrade === "1";
  const session = await getServerSession(authOptions);

  if (!session?.user) redirect("/auth/signin");

  const userId = session.user.id as string;

  // ── D1에서 실데이터 조회 ──────────────────────────────────────────
  let subscription: Subscription | null = null;
  let referralCount = 0;
  let telegramLinked = false;
  let whaleSections: Sections | null = null;
  let whaleUpdatedAt: string | null = null;
  let whaleUsSections: Sections | null = null;
  let whaleUsUpdatedAt: string | null = null;

  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    const db = ctx?.env?.DB as import("@cloudflare/workers-types").D1Database | undefined;
    if (db) {
      type WhaleFeedRow = { program_items: string | null; foreign_items: string | null; volume_items: string | null; value_items: string | null; updated_at: string | null };
      const [sub, referrals, userRow, whaleRow, whaleUsRow] = await Promise.all([
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
        db
          .prepare("SELECT program_items, foreign_items, volume_items, value_items, updated_at FROM whale_feed WHERE market = 'KR'")
          .first<WhaleFeedRow>(),
        db
          .prepare("SELECT program_items, foreign_items, volume_items, value_items, updated_at FROM whale_feed WHERE market = 'US'")
          .first<WhaleFeedRow>(),
      ]);

      subscription = sub;
      referralCount = referrals?.count ?? 0;
      telegramLinked = !!userRow?.telegram_id;

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const parse = (s: string | null) => JSON.parse(s ?? "[]") as any[];

      if (whaleRow) {
        whaleSections = {
          program: parse(whaleRow.program_items),
          foreign: parse(whaleRow.foreign_items),
          volume: parse(whaleRow.volume_items),
          value: parse(whaleRow.value_items),
        };
        whaleUpdatedAt = whaleRow.updated_at;
      }

      if (whaleUsRow) {
        whaleUsSections = {
          program: parse(whaleUsRow.program_items),
          foreign: parse(whaleUsRow.foreign_items),
          volume: parse(whaleUsRow.volume_items),
          value: parse(whaleUsRow.value_items),
        };
        whaleUsUpdatedAt = whaleUsRow.updated_at;
      }

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
  const provider = userId.split("_")[0];

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
  const botUsername = process.env.TELEGRAM_BOT_USERNAME ?? "Stock_Now_Bot";
  const inviteLink = `https://t.me/${botUsername}?start=ref_${code}`;

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white">
      <OnboardingTourLoader usFirst={!!(whaleUsUpdatedAt && whaleUpdatedAt ? whaleUsUpdatedAt > whaleUpdatedAt : !!whaleUsUpdatedAt)} />
      <div className="flex">
        <DashboardSidebar user={session.user} provider={provider} />

        {/* Main */}
        <main className="flex-1">
          <Suspense fallback={null}>
            <PaymentBanner />
          </Suspense>

          {showUpgradeBanner && (
            <div className="mx-4 mt-4 lg:mx-12 max-w-4xl lg:mx-auto rounded-2xl border border-purple-500/30 bg-gradient-to-r from-purple-500/10 to-blue-500/10 px-5 py-4 flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold text-purple-300">🔒 프리미엄 전용 페이지입니다</p>
                <p className="text-xs text-gray-400 mt-0.5">컨센서스·트럼프 임팩트 페이지는 유료 구독 후 이용하실 수 있습니다.</p>
              </div>
              <PremiumUpgradeButton />
            </div>
          )}

          <div className="px-4 pt-6 pb-28 lg:px-12 lg:pt-10 lg:pb-12 max-w-4xl mx-auto">
            {/* Header */}
            <header className="mb-6 flex items-start justify-between gap-3">
              <div>
                <h2 className="text-2xl lg:text-3xl font-bold mb-1">
                  안녕하세요, {session.user.name?.split(" ")[0] || "반가워요"}! 👋
                </h2>
                <p className="text-gray-500 text-sm">오늘은 국내 거래소 고래 수급이 활발합니다.</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className={`px-3 py-1.5 rounded-full border font-medium text-xs flex items-center gap-1.5 ${!isPaid
                  ? "bg-white/5 text-gray-400 border-white/10"
                  : "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                  }`}>
                  <span className={`w-1.5 h-1.5 rounded-full ${!isPaid ? "bg-gray-500" : "bg-emerald-500 animate-pulse"}`} />
                  {planDisplay}
                </span>
                <Link
                  href="/changelog"
                  className="text-[11px] text-gray-600 hover:text-purple-400 transition-colors font-mono"
                >
                  {CURRENT_VERSION}
                </Link>
              </div>
            </header>

            <div className="space-y-4 lg:grid lg:grid-cols-3 lg:gap-6 lg:space-y-0">
              {/* Subscription Card */}
              <div className="lg:col-span-2 p-6 lg:p-8 rounded-2xl lg:rounded-3xl bg-gradient-to-br from-purple-600/20 to-blue-600/20 border border-white/10 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-6 text-7xl opacity-10 blur-sm pointer-events-none">👑</div>
                <div className="flex items-start justify-between mb-4">
                  <h3 className="text-base font-bold text-gray-300">내 구독 정보</h3>
                  {subscription?.expires_at && (
                    <div className="text-right">
                      <div className="text-gray-500 text-[10px] mb-0.5">만료 예정일</div>
                      <div className="text-sm font-semibold">{expiresDisplay}</div>
                    </div>
                  )}
                </div>
                <div className="text-3xl lg:text-4xl font-black mb-2 tracking-tight">{planDisplay}</div>
                <p className="text-gray-400 text-sm mb-5 leading-relaxed">
                  {plan === "trial"
                    ? `7일 무료 체험 중입니다. ${expiresDisplay}에 종료됩니다.`
                    : isPaid
                      ? "구독 중입니다. 모든 기능을 사용할 수 있습니다."
                      : "무료 플랜을 이용 중입니다."}
                </p>
                <div className="flex flex-col sm:flex-row gap-2">
                  <div id="tour-telegram-btn"><TelegramLinkButton isLinked={telegramLinked} /></div>
                  <div id="tour-upgrade-btn"><PremiumUpgradeButton isRenewal={isPaid} expiresAt={subscription?.expires_at} /></div>
                </div>
              </div>

              {/* Referral Card */}
              <div className="p-6 lg:p-8 rounded-2xl lg:rounded-3xl bg-white/[0.03] border border-white/10">
                <h3 className="text-base font-bold mb-1">친구 초대 혜택</h3>
                <p className="text-gray-400 text-xs mb-4 leading-relaxed">
                  친구 1명 초대 시 <span className="text-white font-semibold">+7일</span> · 최대 20명
                </p>
                <div className="p-3 rounded-xl bg-black/40 border border-white/5 mb-3">
                  <div className="text-[10px] text-gray-500 uppercase font-bold tracking-widest mb-1">내 초대 코드</div>
                  <div className="flex items-center justify-between font-mono text-purple-400">
                    <span className="text-sm">{referralCode}</span>
                    <CopyButton text={inviteLink} label="🔗 초대 링크 복사" />
                  </div>
                </div>
                <div className="flex items-center justify-between text-sm text-gray-500">
                  <span>초대한 친구</span>
                  <span className="font-bold text-white">{referralCount}명 (+{referralCount * 7}일)</span>
                </div>
              </div>

              {/* US가 더 최근에 업데이트됐으면 위에 표시 */}
              {(() => {
                const usIsNewer = whaleUsUpdatedAt && whaleUpdatedAt
                  ? whaleUsUpdatedAt > whaleUpdatedAt
                  : !!whaleUsUpdatedAt;

                const krPanel = (
                  <div id="tour-kr-market" className="lg:col-span-3 p-6 lg:p-8 rounded-2xl lg:rounded-3xl bg-white/[0.03] border border-white/10">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-base font-bold">🇰🇷 국내 수급 현황</h3>
                        <div className="flex items-center gap-2 mt-0.5">
                          <p className="text-[10px] text-gray-600">프로그램·외국인·거래량 상위 종목 (5분 갱신)</p>
                          {whaleUpdatedAt && (
                            <span className="text-[9px] text-gray-400 font-medium bg-white/[0.03] px-1.5 py-0.5 rounded border border-white/5 whitespace-nowrap">
                              🕒 최종 업데이트: {formatKST(whaleUpdatedAt)}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="flex items-center gap-1 text-[10px] text-emerald-500">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        LIVE
                      </span>
                    </div>
                    <WhaleFeedPanel sections={whaleSections} updated_at={whaleUpdatedAt} tabs={KR_TABS} />
                  </div>
                );

                const usPanel = (
                  <div id="tour-us-market" className="lg:col-span-3 p-6 lg:p-8 rounded-2xl lg:rounded-3xl bg-white/[0.03] border border-white/10">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-base font-bold">🇺🇸 미국 시장 현황</h3>
                        <div className="flex items-center gap-2 mt-0.5">
                          <p className="text-[10px] text-gray-600">주요 지수·섹터·급등락 종목 (5분 갱신)</p>
                          {whaleUsUpdatedAt && (
                            <span className="text-[9px] text-gray-400 font-medium bg-white/[0.03] px-1.5 py-0.5 rounded border border-white/5 whitespace-nowrap">
                              🕒 최종 업데이트: {formatKST(whaleUsUpdatedAt)}
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="flex items-center gap-1 text-[10px] text-blue-400">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse" />
                        LIVE
                      </span>
                    </div>
                    <WhaleFeedPanel
                      sections={whaleUsSections}
                      updated_at={whaleUsUpdatedAt}
                      tabs={US_TABS}
                      emptyMessage="미국장 개장 시간에 자동으로 업데이트됩니다."
                    />
                  </div>
                );

                return usIsNewer ? <>{usPanel}{krPanel}</> : <>{krPanel}{usPanel}</>;
              })()}
            </div>
          </div>
        </main>
      </div>
      <MobileNav />
    </div>
  );
}
