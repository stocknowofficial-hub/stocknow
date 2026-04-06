'use client';

import { useEffect, useState } from 'react';

const PRICE_DATA = [61200, 62500, 61800, 63400, 62900, 64100, 63700, 65200, 64800, 65900, 65400, 66800, 66200, 67500, 67100, 68400, 68900, 70100, 69800, 71200];

const ALERTS = [
  { id: 1, coin: 'BTC', amount: '1,247 BTC', from: '익명 지갑', to: 'Binance', bull: true, age: '방금' },
  { id: 2, coin: 'ETH', amount: '5,832 ETH', from: 'Kraken', to: '익명 지갑', bull: false, age: '2분 전' },
  { id: 3, coin: 'XRP', amount: '42.1M XRP', from: '익명 지갑', to: 'Upbit', bull: true, age: '5분 전' },
  { id: 4, coin: 'SOL', amount: '98,200 SOL', from: 'Coinbase', to: '익명 지갑', bull: false, age: '8분 전' },
];

const W = 400, H = 130;
const min = Math.min(...PRICE_DATA);
const max = Math.max(...PRICE_DATA);
const xStep = W / (PRICE_DATA.length - 1);
const yOf = (v: number) => H - 8 - ((v - min) / (max - min)) * (H - 20);
const points = PRICE_DATA.map((p, i) => [i * xStep, yOf(p)] as [number, number]);
const linePath = points.map(([x, y], i) => `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`).join(' ');
const areaPath = `${linePath} L ${W} ${H} L 0 ${H} Z`;
const lastPt = points[points.length - 1];

const currentPrice = PRICE_DATA[PRICE_DATA.length - 1];
const prevPrice = PRICE_DATA[0];
const changePct = (((currentPrice - prevPrice) / prevPrice) * 100).toFixed(2);

export function HeroDashboard() {
  const [pulse, setPulse] = useState(false);
  const [highlighted, setHighlighted] = useState(0);
  const [visibleCount, setVisibleCount] = useState(0);

  useEffect(() => {
    const p = setInterval(() => setPulse(v => !v), 900);
    const h = setInterval(() => setHighlighted(v => (v + 1) % ALERTS.length), 2800);
    // Stagger alert appearance
    let count = 0;
    const show = setInterval(() => {
      count++;
      setVisibleCount(count);
      if (count >= ALERTS.length) clearInterval(show);
    }, 300);
    return () => { clearInterval(p); clearInterval(h); clearInterval(show); };
  }, []);

  return (
    <div className="flex w-full h-full text-white">
      {/* ── Left: Chart ── */}
      <div className="flex-1 flex flex-col px-5 py-4 min-w-0">
        {/* Top stats */}
        <div className="flex items-end gap-3 mb-1">
          <div>
            <div className="text-[10px] text-gray-600 font-mono mb-0.5">BTC / USDT · 1H</div>
            <span className="text-xl md:text-2xl font-bold font-mono tracking-tight">
              ${currentPrice.toLocaleString()}
            </span>
          </div>
          <span className="text-emerald-400 text-xs font-semibold mb-0.5">▲ +{changePct}%</span>
          <span className="text-gray-600 text-[10px] font-mono mb-1 ml-auto">VOL $2.14B</span>
        </div>

        {/* SVG price chart */}
        <div className="flex-1 relative min-h-0">
          <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="none">
            <defs>
              <linearGradient id="cg" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#10b981" stopOpacity="0.25" />
                <stop offset="100%" stopColor="#10b981" stopOpacity="0" />
              </linearGradient>
            </defs>
            {/* Horizontal grid */}
            {[0.3, 0.6, 0.9].map(t => (
              <line key={t} x1="0" y1={H * t} x2={W} y2={H * t}
                stroke="white" strokeOpacity="0.04" strokeWidth="1" />
            ))}
            {/* Area */}
            <path d={areaPath} fill="url(#cg)" />
            {/* Line */}
            <path d={linePath} fill="none" stroke="#10b981" strokeWidth="1.8"
              strokeLinejoin="round" strokeLinecap="round" />
            {/* Animated end dot */}
            <circle cx={lastPt[0]} cy={lastPt[1]} r="2.5" fill="#10b981" />
            {pulse && (
              <circle cx={lastPt[0]} cy={lastPt[1]} r="7" fill="#10b981" fillOpacity="0.2" />
            )}
            {/* Price label at end */}
            <rect x={lastPt[0] + 5} y={lastPt[1] - 9} width="52" height="14" rx="3"
              fill="#10b981" fillOpacity="0.15" />
            <text x={lastPt[0] + 31} y={lastPt[1] + 1} textAnchor="middle"
              fill="#10b981" fontSize="9" fontFamily="monospace">
              ${(currentPrice / 1000).toFixed(1)}K
            </text>
          </svg>
        </div>

        {/* Volume bars */}
        <div className="flex items-end gap-px h-5 mt-1">
          {PRICE_DATA.map((p, i) => {
            const isBull = i === 0 || p >= PRICE_DATA[i - 1];
            const h = 30 + ((p - min) / (max - min)) * 70;
            return (
              <div key={i} className="flex-1 rounded-[1px]"
                style={{
                  height: `${h}%`,
                  backgroundColor: isBull ? 'rgba(16,185,129,0.35)' : 'rgba(239,68,68,0.3)',
                }} />
            );
          })}
        </div>

        {/* Bottom indicators */}
        <div className="flex items-center gap-4 mt-2">
          {[
            { label: 'RSI', val: '67.4', color: 'text-amber-400' },
            { label: 'MACD', val: '+124', color: 'text-emerald-400' },
            { label: 'OBV', val: '▲', color: 'text-purple-400' },
          ].map(ind => (
            <div key={ind.label} className="flex items-center gap-1">
              <span className="text-[9px] text-gray-600 font-mono">{ind.label}</span>
              <span className={`text-[9px] font-bold font-mono ${ind.color}`}>{ind.val}</span>
            </div>
          ))}
          <div className="ml-auto flex items-center gap-1.5">
            <div className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500" />
            </div>
            <span className="text-[9px] text-emerald-400 font-mono">LIVE</span>
          </div>
        </div>
      </div>

      {/* ── Divider ── */}
      <div className="hidden md:block w-px bg-white/5 my-3 shrink-0" />

      {/* ── Right: Whale Alerts ── */}
      <div className="hidden md:flex w-48 shrink-0 flex-col p-3 gap-1.5 overflow-hidden">
        <div className="flex items-center gap-1.5 mb-0.5">
          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">🐋 고래 감지</span>
        </div>

        {ALERTS.map((alert, i) => {
          const isActive = i === highlighted;
          return (
            <div
              key={alert.id}
              style={{
                opacity: i < visibleCount ? 1 : 0,
                transform: i < visibleCount ? 'translateY(0)' : 'translateY(8px)',
                transition: 'opacity 0.4s ease, transform 0.4s ease, border-color 0.4s, background-color 0.4s',
              }}
              className={`p-2 rounded-xl border text-xs ${
                isActive
                  ? alert.bull
                    ? 'border-emerald-500/40 bg-emerald-500/10'
                    : 'border-red-500/40 bg-red-500/10'
                  : 'border-white/[0.06] bg-white/[0.02]'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-white/90 text-[11px]">{alert.coin}</span>
                <span className={`text-[9px] font-semibold ${alert.bull ? 'text-emerald-400' : 'text-red-400'}`}>
                  {alert.bull ? '▲ 입금' : '▼ 출금'}
                </span>
              </div>
              <div className="text-gray-400 text-[9px] font-mono mt-0.5">{alert.amount}</div>
              <div className="text-gray-600 text-[9px] mt-0.5 truncate">
                {alert.from} → {alert.to}
              </div>
              <div className="text-gray-700 text-[9px] mt-0.5">{alert.age}</div>
            </div>
          );
        })}

        {/* AI Signal */}
        <div className="mt-auto pt-1 border-t border-white/5">
          <div className={`flex items-center gap-1.5 px-2 py-1.5 rounded-lg transition-colors duration-700 ${
            pulse ? 'bg-purple-500/10' : 'bg-purple-500/5'
          }`}>
            <span className="text-[10px]">🤖</span>
            <span className="text-[9px] text-purple-400 font-semibold">AI 분석 중...</span>
          </div>
        </div>
      </div>
    </div>
  );
}
