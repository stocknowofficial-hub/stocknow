import Link from "next/link";
import { HeroDashboard } from "@/components/HeroDashboard";

async function getRecentHits() {
  try {
    const { getCloudflareContext } = require('@opennextjs/cloudflare');
    const ctx = getCloudflareContext();
    const db = ctx?.env?.DB;
    if (!db) return null;
    const { results } = await db.prepare(`
      SELECT target, prediction, direction, price_change_pct, source, created_at
      FROM predictions
      WHERE result = 'hit' AND price_change_pct IS NOT NULL
      ORDER BY created_at DESC
      LIMIT 3
    `).all();
    const { total, hits } = (await db.prepare(`
      SELECT COUNT(*) as total, SUM(CASE WHEN result='hit' THEN 1 ELSE 0 END) as hits
      FROM predictions WHERE result IS NOT NULL
    `).first()) as { total: number; hits: number };
    return { hits: results as { target: string; prediction: string; direction: string; price_change_pct: number; source: string; created_at: string }[], total, hitCount: hits };
  } catch { return null; }
}

export default async function FeaturesPage() {
  const recentData = await getRecentHits();
  return (
    <main className="min-h-screen bg-[#0a0a0c] text-white selection:bg-purple-500/30 font-sans">
      {/* Background Decorative Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-purple-600/10 blur-[120px] rounded-full" />
        <div className="absolute top-[20%] -right-[10%] w-[35%] h-[35%] bg-blue-600/10 blur-[120px] rounded-full" />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-6 mx-auto max-w-7xl">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl flex items-center justify-center font-bold text-xl shadow-lg shadow-purple-500/20">
            S
          </div>
          <span className="text-xl font-bold tracking-tight">StockNow</span>
        </Link>
        <div className="flex items-center gap-6">
          <Link href="/auth/signin" className="px-5 py-2.5 rounded-full bg-white/5 hover:bg-white/10 transition-all border border-white/10 text-sm font-medium">
            로그인
          </Link>
          <Link href="/dashboard" className="px-5 py-2.5 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 hover:opacity-90 transition-all text-sm font-semibold shadow-lg shadow-purple-500/20">
            시작하기
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 px-6 pt-24 pb-32 mx-auto max-w-7xl text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-semibold mb-8">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500"></span>
          </span>
          AI 시장 분석 · 실시간 수급 감지 시스템 v2.0
        </div>

        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8 leading-[1.1]">
          왜 올랐는지, 왜 떨어졌는지 <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-blue-400 to-emerald-400">
            AI가 이유를 찾아드립니다
          </span>
        </h1>

        <p className="text-gray-400 text-lg md:text-xl max-w-2xl mx-auto mb-12 leading-relaxed">
          실시간 수급 흐름부터 증권사 리포트 분석, AI 예측까지. <br />
          시장의 맥락을 한눈에 파악하고 기회를 놓치지 마세요.
        </p>

        <div className="flex flex-row items-center justify-center gap-4">
          <Link href="/dashboard" className="px-8 py-4 rounded-2xl bg-white text-black font-bold text-lg hover:scale-[1.02] transition-all shadow-xl shadow-white/5">
            지금 시작하기
          </Link>
          <Link href="/" className="px-8 py-4 rounded-2xl bg-white/5 border border-white/10 font-bold text-lg hover:bg-white/10 transition-all backdrop-blur-sm">
            서비스 소개
          </Link>
        </div>

        {/* Hero Image Mockup Area */}
        <div className="mt-20 relative px-4 mx-auto max-w-5xl">
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-purple-600/5 blur-[120px] rounded-full pointer-events-none" />
          <div className="relative rounded-3xl border border-white/10 overflow-hidden shadow-[0_0_50px_rgba(168,85,247,0.15)] bg-[#0c0c0e]/80 backdrop-blur-xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/5 bg-white/[0.03]">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/40" />
                  <div className="w-3 h-3 rounded-full bg-amber-500/40" />
                  <div className="w-3 h-3 rounded-full bg-emerald-500/40" />
                </div>
                <div className="ml-4 px-3 py-1 rounded-md bg-white/5 text-[10px] text-gray-500 font-mono tracking-wider">
                  STK-ANALYTICS-ENGINE-v2.0
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="h-1.5 w-12 rounded-full bg-white/5" />
                <div className="h-1.5 w-12 rounded-full bg-white/5" />
              </div>
            </div>
            <div className="relative aspect-[4/3] md:aspect-[21/9] overflow-hidden">
              <div className="absolute inset-0 opacity-[0.03] pointer-events-none"
                style={{ backgroundImage: 'linear-gradient(to right, #fff 1px, transparent 1px), linear-gradient(to bottom, #fff 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
              <HeroDashboard />
            </div>
          </div>
        </div>
      </section>

      {/* Recent Hits Preview */}
      {recentData && recentData.hits.length > 0 && (
        <section className="relative z-10 px-6 pb-16 mx-auto max-w-7xl">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                🎯 최근 AI 적중 예측
              </h2>
              {recentData.total > 0 && (
                <p className="text-xs text-gray-500 mt-0.5">
                  총 {recentData.total}건 확정 · 적중률 {Math.round((recentData.hitCount / recentData.total) * 100)}%
                </p>
              )}
            </div>
            <Link href="/history" className="text-xs text-purple-400 hover:text-purple-300 transition-colors">
              전체 보기 →
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {recentData.hits.map((h, i) => {
              const up = h.direction === 'up';
              const pct = h.price_change_pct;
              return (
                <div key={i} className="rounded-2xl bg-emerald-500/5 border border-emerald-500/20 p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-gray-400">{h.target}</span>
                    <span className={`text-sm font-black ${pct >= 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {pct >= 0 ? '+' : ''}{pct.toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-xs text-gray-300 leading-snug line-clamp-2">{h.prediction}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className={`text-[10px] font-bold ${up ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {up ? '↑ 상승 예측' : '↓ 하락 예측'}
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">✅ 적중</span>
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-center text-[10px] text-gray-700 mt-4">※ 과거 성과는 미래 수익을 보장하지 않습니다.</p>
        </section>
      )}

      {/* Features Grid */}
      <section className="relative z-10 px-6 py-24 mx-auto max-w-7xl">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
          {[
            { title: "실시간 수급 감지", desc: "국내외 급등락 종목의 수급 흐름을 실시간으로 포착하고 이유를 분석합니다.", icon: "⚡", color: "from-amber-400 to-orange-500" },
            { title: "AI 종합 분석", desc: "증권사 리포트를 분석해 주목 종목을 추려내고, AI가 상승·하락 예측과 근거를 제공합니다.", icon: "🤖", color: "from-purple-400 to-blue-500" },
            { title: "텔레그램 즉시 알림", desc: "포착된 기회는 즉시 텔레그램으로 전송됩니다.", icon: "📱", color: "from-blue-400 to-emerald-500" }
          ].map((f, i) => (
            <div key={i} className="group p-8 rounded-[2rem] bg-white/[0.02] border border-white/10 hover:border-purple-500/30 transition-all duration-500 hover:bg-white/[0.04]">
              <div className={`w-12 h-12 rounded-2xl bg-gradient-to-br ${f.color} flex items-center justify-center text-2xl mb-6 shadow-lg shadow-black/20 group-hover:scale-110 transition-transform`}>
                {f.icon}
              </div>
              <h3 className="text-xl font-bold mb-3">{f.title}</h3>
              <p className="text-gray-500 leading-relaxed text-sm md:text-base">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="relative z-10 border-t border-white/5 py-10 px-6">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg flex items-center justify-center font-bold text-xs">
                S
              </div>
              <span className="text-sm font-semibold text-gray-400">StockNow</span>
              <span className="text-gray-700 text-xs ml-2">클라우드 브릿지 · 사업자 224-29-01931</span>
            </div>
            <div className="flex items-center gap-6 text-xs text-gray-600">
              <Link href="/terms" className="hover:text-gray-400 transition-colors">이용약관</Link>
              <Link href="/privacy" className="hover:text-gray-400 transition-colors font-semibold text-gray-500">개인정보처리방침</Link>
              <Link href="/refund" className="hover:text-gray-400 transition-colors">환불정책</Link>
              <a href="mailto:stocknow.official@gmail.com" className="hover:text-gray-400 transition-colors">문의</a>
            </div>
          </div>
          <p className="text-center text-xs text-gray-700 mt-6">
            © 2026 클라우드 브릿지. 본 서비스는 투자 참고 정보를 제공하며, 투자 결과에 대한 책임은 이용자 본인에게 있습니다.
          </p>
        </div>
      </footer>
    </main>
  );
}
