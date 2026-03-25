import Link from "next/link";
import { HeroDashboard } from "@/components/HeroDashboard";

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
          <Link href="/features" className="px-8 py-4 rounded-2xl bg-white/5 border border-white/10 font-bold text-lg hover:bg-white/10 transition-all backdrop-blur-sm">
            기능 소개
          </Link>
        </div>

        {/* Hero Image Mockup Area */}
        <div className="mt-20 relative px-4 mx-auto max-w-5xl">
          {/* Decorative Background Glows */}
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[120%] h-[120%] bg-purple-600/5 blur-[120px] rounded-full pointer-events-none" />
          
          <div className="relative rounded-3xl border border-white/10 overflow-hidden shadow-[0_0_50px_rgba(168,85,247,0.15)] bg-[#0c0c0e]/80 backdrop-blur-xl">
            {/* Window Top Bar */}
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
            
            <div className="relative aspect-[16/8] md:aspect-[21/9] overflow-hidden">
              {/* Grid background */}
              <div className="absolute inset-0 opacity-[0.03] pointer-events-none"
                style={{ backgroundImage: 'linear-gradient(to right, #fff 1px, transparent 1px), linear-gradient(to bottom, #fff 1px, transparent 1px)', backgroundSize: '40px 40px' }} />
              <HeroDashboard />
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section className="relative z-10 px-6 py-24 mx-auto max-w-7xl">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 text-left">
          {[
            { title: "실시간 고래 감지", desc: "주요 거래소의 대량 입출금을 초 단위로 추적합니다.", icon: "⚡", color: "from-amber-400 to-orange-500" },
            { title: "AI 수급 분석", desc: "Gemini AI가 수급의 의도와 향후 흐름을 예측합니다.", icon: "🤖", color: "from-purple-400 to-blue-500" },
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
    </main>
  );
}
