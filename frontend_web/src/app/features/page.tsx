'use client';

import Link from 'next/link';
import { useState } from 'react';

/* ── 데이터 ─────────────────────────────────────────── */
const STOCKS = [
  { name: '대우건설',        change: +18.18, price: '19,110', bull: true  },
  { name: '삼천당제약',       change: +14.08, price: '907,000', bull: true  },
  { name: '펩트론',          change:  +8.97, price: '346,000', bull: true  },
  { name: '레인보우로보틱스',  change:  -8.21, price: '659,000', bull: false },
  { name: '카카오페이',       change:  +6.81, price: '64,300',  bull: true  },
  { name: 'LIG넥스원',       change:  -5.84, price: '661,000', bull: false },
  { name: '대한항공',        change:  +7.33, price: '26,350',  bull: true  },
  { name: '포스코인터내셔널',  change:  +7.24, price: '77,000',  bull: true  },
  { name: 'NH투자증권',      change:  +6.58, price: '35,600',  bull: true  },
  { name: '리가켐바이오',     change:  +6.55, price: '213,000', bull: true  },
  { name: 'LG',             change:  +5.52, price: '95,500',  bull: true  },
  { name: '한화에어로스페이스', change:  -4.00, price: '1,320,000', bull: false },
  { name: '삼성에피스홀딩스',  change:  +3.75, price: '552,000', bull: true  },
  { name: '삼성증권',        change:  +3.75, price: '102,300', bull: true  },
];

const KR_BRIEFING = [
  { icon: '📅', title: '오늘의 일정', items: ['미국 증시 네 마녀의 날 — 글로벌 파생상품 대규모 계약 만기', '주간 신규 실업수당 청구 건수 및 필라델피아 연은 제조업 지수', '전일 연준 금리 동결(5.25~5.50%) 여파 반영 예정'] },
  { icon: '📈', title: '시장 전망', items: ['미국 3대 지수 1%대 하락 마감 → 국내 하방 압력 작용', '중동 지정학 리스크로 인한 위험 자산 회피 현상 뚜렷', 'AI·반도체 실적 기대감이 하단을 지지 — 종목별 차별화 예상'] },
  { icon: '⚠️', title: '리스크 및 변수', items: ['브렌트유 배럴당 $111 돌파 — 스태그플레이션 우려', '고금리 장기화 → 달러 강세, 외국인 이탈 가능성', '네 마녀의 날 장 막판 대규모 매물 출회 변수'] },
  { icon: '🧐', title: '관전 포인트', items: ['정유·에너지·해운 관련주 단기 수혜 지속 여부', '반도체·AI 주도주의 반등 탄력 확인', '개인 저점 매수세의 코스피 지지선 방어 여부'] },
];

const US_BRIEFING = [
  { icon: '📅', title: '주요 이슈', items: ['연준 FOMC 금리 동결 결정 (5.25~5.50% 유지)', '파월 의장 "데이터 의존적" 발언 — 금리 인하 시기 불투명', '엔비디아 실적 호조에도 차익 실현 매물 출회'] },
  { icon: '📈', title: '지수 현황', items: ['S&P500 -1.14%  |  나스닥 -1.43%  |  다우 -0.96%', '빅테크 전반 약세 속 에너지·정유 섹터 강세', 'VIX 공포지수 23.4 — 단기 변동성 확대'] },
  { icon: '⚠️', title: '주목 이슈', items: ['PCE 물가지수 발표 예정 — 인플레 재가속 여부 확인 필요', '테슬라 중국 판매량 부진 우려 지속', '달러 인덱스 105.8 — 신흥국 통화 압박'] },
  { icon: '🧐', title: '내일 전망', items: ['네 마녀의 날 변동성 확대 대비 필요', '에너지·방산주 단기 강세 흐름 지속 예상', '나스닥 20,000선 지지 여부 주목'] },
];

const AI_CARDS = [
  {
    stock: '한화솔루션', change: '+11.75%', price: '55,600원',
    cause: '중동발 지정학 위기 심화로 태양광 가격 경쟁력 부각. 미국 솔라 허브 IRA 세액공제(AMPC) 본격화 → 실적 턴어라운드 기대.',
    verdict: '🐂 긍정', color: 'emerald', emoji: '😍',
    note: '전일 브리핑 "중동 리스크 → 대체 에너지 부각" 예측과 일치',
  },
  {
    stock: '포스코인터내셔널', change: '+6.68%', price: '76,600원',
    cause: 'LNG·천연가스 가격 급등으로 가스전 업스트림 자산 수익성 개선 기대. 호주 세넥스 에너지 증산 모멘텀도 유효.',
    verdict: '🐂 긍정', color: 'emerald', emoji: '😍',
    note: '전일 브리핑 "지정학 리스크 → 에너지 가격 급등" 예측과 일치',
  },
  {
    stock: '레인보우로보틱스', change: '-8.21%', price: '659,000원',
    cause: '삼성전자 지분 추가 취득 기대 선반영 후 실망 매물 출회. 과도한 밸류에이션 부담으로 기관 차익 실현.',
    verdict: '🐻 부정', color: 'red', emoji: '😨',
    note: '단기 과열 경고 브리핑 이후 예측 방향대로 급락',
  },
];

const TELE_MSGS = [
  { time: '오전 8:00', type: 'briefing', text: '🇰🇷 한국장 개장 브리핑\n중동 리스크·네 마녀의 날 변동성 확대 예상. 에너지·정유 수혜 관심.' },
  { time: '오전 9:10', type: 'alert', text: '📢 급등 포착!\n삼천당제약 +14.08% 🔥\n한화솔루션 +11.75% 🔥\n펩트론 +8.97% 🔥' },
  { time: '오전 9:11', type: 'ai', text: '💡 AI 심층분석 | 한화솔루션\n태양광 가격 경쟁력 + IRA 세액공제 본격화\n→ 🐂 긍정 | 😍 호재' },
  { time: '오후 3:57', type: 'alert', text: '📊 실시간 현황판 업데이트\n급등 29종목 / 급락 8종목\n→ 전체 리스트 보기 ↗' },
  { time: '오후 4:10', type: 'briefing', text: '🇰🇷 한국장 마감 브리핑\n코스피 +0.3% 방어. 에너지·해운 강세 / 방산 약세.' },
];

const PLANS = [
  { name: 'FREE', sub: '무료', badge: 'bg-gray-500/20 text-gray-400', border: 'border-white/10', features: ['대시보드 접근', '기본 시장 정보 열람', '텔레그램 계정 연동'], cta: '무료로 시작', href: '/dashboard', highlight: false },
  { name: 'TRIAL', sub: '7일 무료 체험', badge: 'bg-cyan-500/20 text-cyan-400', border: 'border-cyan-500/50', features: ['FREE 전체 포함', '실시간 급등/급락 알림', 'AI 심층분석 리포트', '장 브리핑 (한국/미국)', 'VIP 텔레그램 채널 입장'], cta: '무료 체험 시작', href: '/dashboard', highlight: true },
  { name: 'STANDARD', sub: '월 구독', badge: 'bg-purple-500/20 text-purple-400', border: 'border-purple-500/40', features: ['TRIAL 전체 포함', '전 종목 우선 알림', '맞춤형 분석 리포트', '전용 지원 채널'], cta: '구독 시작', href: '/dashboard', highlight: false },
];

const msgColor: Record<string, string> = {
  briefing: 'bg-blue-500/10 border-blue-500/20',
  alert: 'bg-emerald-500/10 border-emerald-500/20',
  ai: 'bg-purple-500/10 border-purple-500/20',
};

/* ── 컴포넌트 ─────────────────────────────────────────── */
export default function FeaturesPage() {
  const [tab, setTab] = useState<'kr' | 'us'>('kr');
  const briefing = tab === 'kr' ? KR_BRIEFING : US_BRIEFING;

  return (
    <main className="min-h-screen bg-[#0a0a0c] text-white font-sans">
      {/* BG glows */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-[10%] -left-[10%] w-[40%] h-[40%] bg-purple-600/8 blur-[140px] rounded-full" />
        <div className="absolute top-[30%] -right-[10%] w-[35%] h-[35%] bg-blue-600/8 blur-[140px] rounded-full" />
        <div className="absolute bottom-[10%] left-[20%] w-[30%] h-[30%] bg-emerald-600/5 blur-[140px] rounded-full" />
      </div>

      {/* Nav */}
      <nav className="relative z-10 flex items-center justify-between px-6 py-5 mx-auto max-w-7xl border-b border-white/5">
        <Link href="/" className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg flex items-center justify-center font-bold text-sm shadow-lg">S</div>
          <span className="text-lg font-bold">StockNow</span>
        </Link>
        <Link href="/dashboard" className="px-5 py-2 rounded-full bg-gradient-to-r from-purple-600 to-blue-600 hover:opacity-90 transition text-sm font-semibold shadow-lg">
          지금 시작하기
        </Link>
      </nav>

      {/* ── S1: Hero ───────────────────────────────────────── */}
      <section className="relative z-10 px-6 pt-24 pb-20 mx-auto max-w-4xl text-center">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-400 text-xs font-semibold mb-8">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-purple-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-purple-500" />
          </span>
          기능 소개
        </div>
        <h1 className="text-4xl md:text-6xl font-bold tracking-tight mb-6 leading-[1.1]">
          매일 수백 개의 종목 중,<br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 via-blue-400 to-emerald-400">
            오늘 움직일 종목을 어떻게 아나요?
          </span>
        </h1>
        <p className="text-gray-400 text-lg max-w-2xl mx-auto leading-relaxed">
          StockNow는 실시간 수급 감지부터 AI 분석, 장 브리핑까지<br />
          주식 시장의 흐름을 통째로 읽어드립니다.
        </p>
      </section>

      {/* ── S2: 실시간 급등/급락 ───────────────────────────── */}
      <section className="relative z-10 px-6 py-24 mx-auto max-w-7xl">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          <div>
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-widest">01 — 실시간 감지</span>
            <h2 className="text-3xl md:text-4xl font-bold mt-3 mb-5 leading-snug">
              ±3% 급등/급락 종목을<br />즉시 포착합니다
            </h2>
            <p className="text-gray-400 leading-relaxed mb-6">
              시가총액 200위 이내 전 종목을 초 단위로 모니터링합니다.
              기준 등락률을 초과하는 순간 자동으로 감지하여 텔레그램으로 전송합니다.
            </p>
            <ul className="space-y-3 text-sm text-gray-400">
              {['시가총액 200위 이내 전 종목 모니터링', '±3% 이상 급등/급락 자동 포착', '실시간 현황판 telegra.ph 자동 업데이트', '한국장·미국장 동시 커버'].map(f => (
                <li key={f} className="flex items-center gap-3">
                  <span className="w-5 h-5 rounded-full bg-emerald-500/20 flex items-center justify-center text-emerald-400 text-xs flex-shrink-0">✓</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>

          {/* Stock list mockup */}
          <div className="rounded-3xl border border-white/10 bg-white/[0.02] overflow-hidden shadow-2xl">
            <div className="px-5 py-4 border-b border-white/5 flex items-center justify-between">
              <div>
                <div className="text-xs text-gray-600 font-mono">2026년 3월 20일 15:57 기준</div>
                <div className="text-sm font-bold mt-0.5">실시간 급등/급락 현황</div>
              </div>
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                <span className="text-[10px] text-emerald-400 font-mono">LIVE</span>
              </div>
            </div>
            <div className="divide-y divide-white/[0.04] max-h-80 overflow-y-auto">
              {STOCKS.map((s, i) => (
                <div key={i} className="flex items-center justify-between px-5 py-3 hover:bg-white/[0.02] transition-colors">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium">{s.name}</span>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-xs text-gray-600 font-mono">{s.price}원</span>
                    <span className={`text-sm font-bold font-mono w-16 text-right ${s.bull ? 'text-emerald-400' : 'text-red-400'}`}>
                      {s.bull ? '🔥' : '💧'} {s.bull ? '+' : ''}{s.change.toFixed(2)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── S3: AI 심층분석 ─────────────────────────────────── */}
      <section className="relative z-10 px-6 py-24 mx-auto max-w-7xl">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          {/* AI cards mockup */}
          <div className="space-y-4 order-2 md:order-1">
            {AI_CARDS.map((c, i) => (
              <div key={i} className={`rounded-2xl border p-5 ${c.color === 'emerald' ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-red-500/20 bg-red-500/5'}`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold">💡 {c.stock}</span>
                    <span className={`text-xs font-bold font-mono ${c.color === 'emerald' ? 'text-emerald-400' : 'text-red-400'}`}>{c.change}</span>
                  </div>
                  <span className="text-lg">{c.emoji}</span>
                </div>
                <p className="text-xs text-gray-400 leading-relaxed mb-2">{c.cause}</p>
                <div className="flex items-center justify-between">
                  <span className={`text-xs font-bold ${c.color === 'emerald' ? 'text-emerald-400' : 'text-red-400'}`}>{c.verdict}</span>
                  <span className="text-[10px] text-gray-600 italic">{c.note}</span>
                </div>
              </div>
            ))}
          </div>

          <div className="order-1 md:order-2">
            <span className="text-xs font-bold text-purple-400 uppercase tracking-widest">02 — AI 분석</span>
            <h2 className="text-3xl md:text-4xl font-bold mt-3 mb-5 leading-snug">
              왜 올랐는지,<br />지속될지 AI가 판단합니다
            </h2>
            <p className="text-gray-400 leading-relaxed mb-6">
              급등 종목이 감지되는 즉시, AI가 핵심 원인을 분석하고
              투자 판단(긍정/부정)까지 제시합니다.
              뉴스를 뒤지지 않아도 됩니다.
            </p>
            <ul className="space-y-3 text-sm text-gray-400">
              {['급등 감지 즉시 AI 자동 분석 시작', '핵심 원인 + 투자 판단 제공', '전일 브리핑 예측과 일치 여부 검증', '감성 분석 (호재/악재/중립)'].map(f => (
                <li key={f} className="flex items-center gap-3">
                  <span className="w-5 h-5 rounded-full bg-purple-500/20 flex items-center justify-center text-purple-400 text-xs flex-shrink-0">✓</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* ── S4: 장 브리핑 ──────────────────────────────────── */}
      <section className="relative z-10 px-6 py-24 mx-auto max-w-7xl">
        <div className="grid md:grid-cols-2 gap-16 items-start">
          <div>
            <span className="text-xs font-bold text-blue-400 uppercase tracking-widest">03 — 장 브리핑</span>
            <h2 className="text-3xl md:text-4xl font-bold mt-3 mb-5 leading-snug">
              장 시작 전부터 마감까지<br />흐름을 놓치지 않습니다
            </h2>
            <p className="text-gray-400 leading-relaxed mb-6">
              한국장과 미국장의 개장·장중·마감 브리핑을 하루 6회 제공합니다.
              일정, 전망, 리스크, 관전 포인트까지 한눈에 파악하세요.
            </p>
            <ul className="space-y-3 text-sm text-gray-400">
              {['한국장 개장/장중/마감 브리핑', '미국장 개장/장중/마감 브리핑', '주요 경제 지표 및 일정 정리', '전일 예측 정확도 검증'].map(f => (
                <li key={f} className="flex items-center gap-3">
                  <span className="w-5 h-5 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 text-xs flex-shrink-0">✓</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>

          {/* Briefing mockup */}
          <div className="rounded-3xl border border-white/10 bg-white/[0.02] overflow-hidden shadow-2xl">
            {/* Tab */}
            <div className="flex border-b border-white/5">
              <button
                onClick={() => setTab('kr')}
                className={`flex-1 py-3 text-sm font-semibold transition-colors ${tab === 'kr' ? 'text-white bg-white/5' : 'text-gray-600 hover:text-gray-400'}`}
              >
                🇰🇷 한국장
              </button>
              <button
                onClick={() => setTab('us')}
                className={`flex-1 py-3 text-sm font-semibold transition-colors ${tab === 'us' ? 'text-white bg-white/5' : 'text-gray-600 hover:text-gray-400'}`}
              >
                🇺🇸 미국장
              </button>
            </div>
            <div className="p-5 space-y-4 max-h-80 overflow-y-auto">
              <div className="text-xs font-bold text-gray-500 font-mono mb-2">
                {tab === 'kr' ? '🇰🇷 한국 증시 개장 브리핑 — 2026.03.20' : '🇺🇸 미국 증시 마감 브리핑 — 2026.03.20'}
              </div>
              {briefing.map((b, i) => (
                <div key={i}>
                  <div className="text-xs font-bold text-gray-300 mb-1.5">{b.icon} {b.title}</div>
                  <ul className="space-y-1">
                    {b.items.map((item, j) => (
                      <li key={j} className="text-xs text-gray-500 leading-relaxed pl-3 border-l border-white/5">
                        {item}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── S5: 텔레그램 ───────────────────────────────────── */}
      <section className="relative z-10 px-6 py-24 mx-auto max-w-7xl">
        <div className="grid md:grid-cols-2 gap-16 items-center">
          {/* Phone mockup */}
          <div className="flex justify-center order-2 md:order-1">
            <div className="relative w-64">
              {/* Phone frame */}
              <div className="rounded-[2.5rem] border-4 border-white/10 bg-[#0c0c0e] overflow-hidden shadow-2xl shadow-purple-500/10">
                {/* Status bar */}
                <div className="bg-[#111] px-5 pt-4 pb-2 flex items-center justify-between">
                  <span className="text-[10px] text-gray-500 font-mono">9:10</span>
                  <div className="flex gap-1">
                    <div className="w-4 h-1.5 rounded-full bg-white/20" />
                    <div className="w-3 h-1.5 rounded-full bg-white/20" />
                  </div>
                </div>
                {/* Channel header */}
                <div className="bg-[#111] px-4 py-3 flex items-center gap-3 border-b border-white/5">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center text-xs font-bold">S</div>
                  <div>
                    <div className="text-xs font-bold">Stock Now VIP</div>
                    <div className="text-[9px] text-gray-600">Premium Channel</div>
                  </div>
                </div>
                {/* Messages */}
                <div className="p-3 space-y-2 bg-[#0a0a0c] min-h-64">
                  {TELE_MSGS.map((m, i) => (
                    <div key={i} className={`rounded-xl border p-2.5 ${msgColor[m.type]}`}>
                      <div className="text-[9px] text-gray-600 font-mono mb-1">{m.time}</div>
                      <div className="text-[10px] text-gray-300 leading-relaxed whitespace-pre-line">{m.text}</div>
                    </div>
                  ))}
                </div>
              </div>
              {/* Glow */}
              <div className="absolute -inset-4 bg-purple-500/10 blur-3xl rounded-full -z-10" />
            </div>
          </div>

          <div className="order-1 md:order-2">
            <span className="text-xs font-bold text-amber-400 uppercase tracking-widest">04 — 텔레그램 VIP</span>
            <h2 className="text-3xl md:text-4xl font-bold mt-3 mb-5 leading-snug">
              포착된 기회는<br />즉시 텔레그램으로 전송됩니다
            </h2>
            <p className="text-gray-400 leading-relaxed mb-6">
              대시보드를 열고 있지 않아도 괜찮습니다.
              급등 감지, AI 분석, 장 브리핑 — 모든 알림이
              VIP 텔레그램 채널로 실시간 전송됩니다.
            </p>
            <ul className="space-y-3 text-sm text-gray-400">
              {['구독 즉시 VIP 채널 1회용 초대 링크 발송', '급등/급락 감지 → 즉시 알림', 'AI 분석 리포트 자동 발송', '만료 시 채널 자동 퇴장 처리'].map(f => (
                <li key={f} className="flex items-center gap-3">
                  <span className="w-5 h-5 rounded-full bg-amber-500/20 flex items-center justify-center text-amber-400 text-xs flex-shrink-0">✓</span>
                  {f}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      {/* ── S6: 플랜 비교 ──────────────────────────────────── */}
      <section className="relative z-10 px-6 py-24 mx-auto max-w-5xl">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold mb-4">지금 바로 시작하세요</h2>
          <p className="text-gray-400">7일 무료 체험으로 모든 기능을 먼저 경험해보세요.</p>
        </div>

        <div className="grid md:grid-cols-3 gap-6">
          {PLANS.map((plan) => (
            <div key={plan.name} className={`relative rounded-3xl border p-8 ${plan.border} ${plan.highlight ? 'bg-white/[0.04]' : 'bg-white/[0.02]'}`}>
              {plan.highlight && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 text-xs font-bold text-white shadow-lg">
                  추천
                </div>
              )}
              <span className={`inline-block px-3 py-1 rounded-full text-xs font-bold mb-4 ${plan.badge}`}>{plan.name}</span>
              <div className="text-2xl font-bold mb-6">{plan.sub}</div>
              <ul className="space-y-3 mb-8">
                {plan.features.map(f => (
                  <li key={f} className="flex items-center gap-2 text-sm text-gray-400">
                    <span className="text-emerald-400 text-xs">✓</span>
                    {f}
                  </li>
                ))}
              </ul>
              <Link
                href={plan.href}
                className={`block w-full text-center py-3 rounded-xl font-semibold text-sm transition-all ${
                  plan.highlight
                    ? 'bg-gradient-to-r from-cyan-500 to-blue-500 hover:opacity-90 text-white shadow-lg'
                    : 'bg-white/5 hover:bg-white/10 text-gray-300 border border-white/10'
                }`}
              >
                {plan.cta}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {/* ── Footer CTA ─────────────────────────────────────── */}
      <section className="relative z-10 px-6 py-24 mx-auto max-w-3xl text-center">
        <h2 className="text-3xl md:text-5xl font-bold mb-6 leading-tight">
          수급의 흐름을<br />
          <span className="bg-clip-text text-transparent bg-gradient-to-r from-purple-400 to-emerald-400">
            지금 바로 읽어보세요
          </span>
        </h2>
        <p className="text-gray-500 mb-10">가입 즉시 7일 무료 체험이 시작됩니다. 카드 등록 불필요.</p>
        <Link href="/dashboard"
          className="inline-block px-12 py-5 rounded-2xl bg-white text-black font-bold text-lg hover:scale-[1.02] transition-all shadow-2xl shadow-white/10">
          지금 시작하기 →
        </Link>
      </section>
    </main>
  );
}
