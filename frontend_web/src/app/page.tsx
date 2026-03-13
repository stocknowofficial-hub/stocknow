import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0a0a0c] text-white selection:bg-purple-500/30 font-sans">
      {/* Background Decorative Elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-purple-600/10 blur-[120px] rounded-full" />
        <div className="absolute top-[20%] -right-[10%] w-[35%] h-[35%] bg-blue-600/10 blur-[120px] rounded-full" />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-6 mx-auto max-w-7xl">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl flex items-center justify-center font-bold text-xl shadow-lg shadow-purple-500/20">
            S
          </div>
          <span className="text-xl font-bold tracking-tight">StockNow</span>
        </div>
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
          실시간 고래 수급 감지 시스템 v2.0
        </div>
        
        <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8 leading-[1.1]">
          수급의 흐름을 <br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-blue-400 to-emerald-400">
            실시간으로 읽다
          </span>
        </h1>
        
        <p className="text-gray-400 text-lg md:text-xl max-w-2xl mx-auto mb-12 leading-relaxed">
          국내외 고래들의 실시간 수급을 AI가 분석합니다. <br />
          텔레그램 알림과 웹 대시보드로 시장의 기회를 놓치지 마세요.
        </p>

        <div className="flex flex-row items-center justify-center gap-4">
          <Link href="/dashboard" className="px-8 py-4 rounded-2xl bg-white text-black font-bold text-lg hover:scale-[1.02] transition-all shadow-xl shadow-white/5">
            지금 시작하기
          </Link>
          <button className="px-8 py-4 rounded-2xl bg-white/5 border border-white/10 font-bold text-lg hover:bg-white/10 transition-all backdrop-blur-sm">
            기능 소개
          </button>
        </div>

        {/* Hero Image Mockup Area */}
        <div className="mt-20 relative px-4 mx-auto max-w-5xl">
          <div className="absolute inset-0 bg-gradient-to-t from-[#0a0a0c] via-transparent to-transparent z-10" />
          <div className="rounded-3xl border border-white/10 overflow-hidden shadow-2xl shadow-purple-500/10 aspect-[16/9] bg-white/5 relative">
            <div className="absolute inset-0 flex items-center justify-center text-white/5 uppercase tracking-[0.2em] font-black text-4xl -rotate-12 select-none">
              StockNow Analytics
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="relative z-10 px-6 py-24 mx-auto max-w-7xl">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { title: "실시간 고래 감지", desc: "주요 거래소의 대량 입출금을 초 단위로 추적합니다.", icon: "⚡" },
            { title: "AI 수급 분석", desc: "Gemini AI가 수급의 의도와 향후 흐름을 예측합니다.", icon: "🤖" },
            { title: "텔레그램 즉시 알림", desc: "포착된 기회는 즉시 텔레그램으로 전송됩니다.", icon: "📱" }
          ].map((f, i) => (
            <div key={i} className="p-8 rounded-3xl bg-white/[0.02] border border-white/10 hover:border-white/20 transition-all">
              <div className="text-3xl mb-4">{f.icon}</div>
              <h3 className="text-xl font-bold mb-3">{f.title}</h3>
              <p className="text-gray-500 leading-relaxed">{f.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
