import Link from "next/link";
import { getServerSession } from "next-auth/next";
import { authOptions } from "@/lib/auth";
import { TelegramLinkButton } from "@/components/TelegramLinkButton";
import { PremiumUpgradeButton } from "@/components/PremiumUpgradeButton";

export default async function DashboardPage() {
  const session = await getServerSession(authOptions);

  // For development, we'll bypass redirect if needed, but in reality:
  // if (!session) redirect("/auth/signin");

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white">
      {/* Sidebar Placeholder */}
      <div className="flex h-screen overflow-hidden">
        <aside className="w-64 border-r border-white/5 bg-white/[0.01] flex flex-col p-6 shrink-0">
          <div className="flex items-center gap-2 mb-12">
            <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg flex items-center justify-center font-bold text-sm">
              S
            </div>
            <span className="text-lg font-bold">StockNow</span>
          </div>

          <nav className="flex-1 space-y-2">
            <Link href="/dashboard" className="flex items-center gap-3 px-4 py-3 rounded-xl bg-white/5 text-purple-400 font-medium transition-all group">
              <span className="p-1.5 bg-purple-500/20 rounded-lg group-hover:bg-purple-500/30 transition-colors">📊</span>
              대시보드
            </Link>
            <Link href="/referrals" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/5 text-gray-400 font-medium transition-all group">
              <span className="p-1.5 bg-white/5 rounded-lg group-hover:bg-white/10 transition-colors">🎁</span>
              초대 혜택
            </Link>
            <Link href="/settings" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-white/5 text-gray-400 font-medium transition-all group">
              <span className="p-1.5 bg-white/5 rounded-lg group-hover:bg-white/10 transition-colors">⚙️</span>
              설정
            </Link>
          </nav>

          <div className="mt-auto pt-6 border-t border-white/5">
            <div className="flex items-center gap-3 px-2">
              <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-gray-700 to-gray-500 overflow-hidden border border-white/10" />
              <div>
                <div className="text-sm font-semibold">{session?.user?.name || "사용자"}</div>
                <div className="text-xs text-gray-500 line-clamp-1">{session?.user?.email || "로그인 필요"}</div>
              </div>
            </div>
          </div>
        </aside>

        <main className="flex-1 overflow-y-auto p-8 lg:p-12">
          <header className="mb-10 flex items-center justify-between">
            <div>
              <h2 className="text-3xl font-bold mb-1">안녕하세요, {session?.user?.name || "반가워요"}! 👋</h2>
              <p className="text-gray-500 text-sm">오늘은 국내 거래소 고래 수급이 활발합니다.</p>
            </div>
            <div className="flex items-center gap-3 text-sm">
              <span className="px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium flex items-center gap-2">
                <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse" />
                D1 DB Connected
              </span>
            </div>
          </header>

          {/* Grid Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Subscription Card */}
            <div className="lg:col-span-2 p-8 rounded-3xl bg-gradient-to-br from-purple-600/20 to-blue-600/20 border border-white/10 relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-8 text-8xl opacity-10 blur-sm pointer-events-none group-hover:scale-110 transition-transform duration-700">👑</div>
              <h3 className="text-xl font-bold mb-6 flex items-center gap-2">
                내 구독 정보
              </h3>
              <div className="flex items-end justify-between">
                <div>
                  <div className="text-4xl font-black mb-2 tracking-tight">FREE PLAN</div>
                  <p className="text-gray-400 text-sm mb-6">현재 무료 플랜을 이용 중입니다. 텔레그램을 연동하여 실시간 알림을 받아보세요.</p>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <TelegramLinkButton />
                    <PremiumUpgradeButton />
                  </div>
                </div>
                <div className="text-right hidden sm:block">
                  <div className="text-gray-500 text-xs mb-1">만료 예정일</div>
                  <div className="text-lg font-semibold">2026. 04. 13</div>
                </div>
              </div>
            </div>

            {/* Referral Card */}
            <div className="p-8 rounded-3xl bg-white/[0.03] border border-white/10 flex flex-col">
              <h3 className="text-xl font-bold mb-4 flex items-center gap-2">
                친구 초대 혜택
              </h3>
              <p className="text-gray-400 text-sm mb-8 leading-relaxed">
                친구 한 명을 초대할 때마다 <br />
                <span className="text-white font-semibold underline decoration-purple-500 underline-offset-4">구독 기간이 1개월 연장</span>됩니다!
              </p>
              
              <div className="space-y-4 mb-4">
                <div className="p-4 rounded-2xl bg-black/40 border border-white/5 space-y-2">
                  <div className="text-[10px] text-gray-500 uppercase font-bold tracking-widest">초대 코드</div>
                  <div className="flex items-center justify-between font-mono text-purple-400">
                    <span>SN-7X2W-99</span>
                    <button className="text-xs px-2 py-1 bg-white/5 rounded-lg hover:bg-white/10 text-white transition-colors">복사</button>
                  </div>
                </div>
              </div>

              <div className="mt-auto pt-4 border-t border-white/5 flex items-center justify-between text-sm">
                <span className="text-gray-500">누적 보상</span>
                <span className="font-bold">0 개월</span>
              </div>
            </div>

            {/* Live Feed Card (Mockup) */}
            <div className="lg:col-span-3 p-8 rounded-3xl bg-white/[0.03] border border-white/10">
              <div className="flex items-center justify-between mb-8">
                <h3 className="text-xl font-bold">실시간 고래 수급 피드</h3>
                <Link href="#" className="text-sm text-purple-400 hover:underline">자세히 보기</Link>
              </div>
              <div className="space-y-4">
                {[
                  { time: "10분 전", title: "비트코인(BTC) 대량 입금 감지", detail: "익명 지갑 -> Upbit (120 BTC)", color: "text-blue-400", bg: "bg-blue-400/10" },
                  { time: "25분 전", title: "이더리움(ETH) 고래 매집", detail: "Binance -> 익명 지갑 (5,000 ETH)", color: "text-purple-400", bg: "bg-purple-400/10" },
                  { time: "1시간 전", title: "리플(XRP) 급격한 수급 변동", detail: "전일 대비 대량 거래 3배 증가", color: "text-emerald-400", bg: "bg-emerald-400/10" }
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-4 p-4 rounded-2xl hover:bg-white/[0.02] transition-colors border border-transparent hover:border-white/5">
                    <div className={`w-12 h-12 rounded-xl ${item.bg} flex items-center justify-center text-xl`}>👁️</div>
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
