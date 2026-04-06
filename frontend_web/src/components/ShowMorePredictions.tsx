'use client';

import { useState, useTransition } from 'react';

interface TradeSetup {
  entry?: string;
  stop_loss?: string;
  target?: string;
}

export interface PredictionRow {
  id: string;
  source: string;
  source_desc: string | null;
  prediction: string;
  direction: string;
  target: string;
  target_code: string | null;
  result: string | null;
  entry_price: number | null;
  current_price: number | null;
  price_change_pct: number | null;
  peak_change_pct: number | null;
  peak_at: string | null;
  hit_change_pct: number | null;
  hit_at: string | null;
  trade_setup: string | null;
  created_at: string;
  expires_at: string;
  confidence: string;
  basis: string | null;
}

export interface WsConsensus {
  ticker: string;
  recommendation: string | null;
  target_price: number | null;
  upside_pct: number | null;
  analyst_count: number | null;
}

function fmtPrice(code: string | null, price: number): string {
  if (code && /^\d{6}$/.test(code)) return `${Math.round(price).toLocaleString()}원`;
  return `$${price.toFixed(0)}`;
}

function DirBadge({ dir }: { dir: string }) {
  if (dir === 'up') return <span className="text-emerald-400 font-bold">↑ 상승</span>;
  if (dir === 'down') return <span className="text-rose-400 font-bold">↓ 하락</span>;
  return <span className="text-gray-400">→ 횡보</span>;
}

function SourceLabel({ source }: { source: string }) {
  if (source === 'trump') return <span className="text-[10px] px-2 py-0.5 rounded bg-red-500/10 text-red-400 border border-red-500/20 font-bold">🏛 트럼프</span>;
  if (source.startsWith('briefing_kr')) return <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20 font-bold">🇰🇷 브리핑</span>;
  if (source.startsWith('briefing_us')) return <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 font-bold">🇺🇸 브리핑</span>;
  return <span className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-gray-400 border border-white/10 font-bold">📑 {source}</span>;
}

function ResultBadge({ result, pct, peakAt }: { result: string | null; pct: number | null; peakAt?: string | null }) {
  if (!result) return <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-gray-500/10 text-gray-500 border border-white/10">진행중</span>;
  if (result === 'hit') return (
    <div className="flex flex-col items-end gap-0.5">
      {pct != null && (
        <div className="flex items-center gap-1">
          <span className="text-sm font-black text-emerald-400">{pct >= 0 ? '+' : ''}{pct.toFixed(1)}%</span>
          {peakAt && <span className="text-[10px] text-gray-500">최고 ({fmtDateShort(peakAt)})</span>}
        </div>
      )}
      <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">✅ 적중</span>
    </div>
  );
  return (
    <div className="flex items-center gap-1.5">
      {pct != null && <span className="text-sm font-black text-rose-400">{pct >= 0 ? '+' : ''}{pct.toFixed(1)}%</span>}
      <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">❌ 빗나감</span>
    </div>
  );
}

function ConfBadge({ conf }: { conf: string }) {
  if (conf?.toUpperCase() === 'HIGH') return <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">HIGH</span>;
  if (conf?.toUpperCase() === 'MEDIUM') return <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/20">MED</span>;
  return null;
}

function PriceRow({ p, ws, ts, showCurrent }: { p: PredictionRow; ws: WsConsensus | null; ts: TradeSetup; showCurrent?: boolean }) {
  const isKr = !!p.target_code && /^\d{6}$/.test(p.target_code);
  const priceSource = isKr ? '네이버' : '월가';
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-500 border-t border-white/5 pt-2">
      {showCurrent && p.entry_price != null && p.current_price != null ? (
        <span>
          <span className="text-gray-500">진입가 {fmtPrice(p.target_code, p.entry_price)}</span>
          <span className="text-gray-600 mx-1">→</span>
          <span className="text-gray-400">현재가 </span>
          <span className={
            p.price_change_pct != null && p.price_change_pct > 0 ? 'text-emerald-400 font-bold' :
            p.price_change_pct != null && p.price_change_pct < 0 ? 'text-rose-400 font-bold' :
            'text-gray-300 font-bold'
          }>{fmtPrice(p.target_code, p.current_price)}</span>
          {p.price_change_pct != null && (
            <span className={p.price_change_pct >= 0 ? 'text-emerald-400 font-bold ml-1' : 'text-rose-400 font-bold ml-1'}>
              ({p.price_change_pct >= 0 ? '+' : ''}{p.price_change_pct.toFixed(1)}%)
            </span>
          )}
        </span>
      ) : p.entry_price != null ? (
        <span>진입가 <span className="text-gray-300 font-medium">{fmtPrice(p.target_code, p.entry_price)}</span></span>
      ) : null}
      {ws?.target_price != null && (
        <span>
          목표가<span className="text-gray-600 ml-0.5">({priceSource})</span>{' '}
          <span className="text-blue-300 font-medium">{fmtPrice(p.target_code, ws.target_price)}</span>
        </span>
      )}
      {ws?.recommendation && (
        <span>투자의견 <span className="text-purple-300 font-medium">{ws.recommendation}</span></span>
      )}
      {ts.target && (
        <span>AI목표 <span className="text-amber-300 font-medium">{ts.target}</span></span>
      )}
      {ts.stop_loss && (
        <span>손절 <span className="text-rose-400/80 font-medium">{ts.stop_loss}</span></span>
      )}
    </div>
  );
}

function PendingCard({ p, wsMap }: { p: PredictionRow; wsMap: Record<string, WsConsensus> }) {
  const daysLeft = Math.ceil((new Date(p.expires_at).getTime() - Date.now()) / 86400000);
  const ws = p.target_code ? (wsMap[p.target_code] ?? null) : null;
  const ts: TradeSetup = p.trade_setup ? JSON.parse(p.trade_setup) : {};
  return (
    <div className="rounded-xl bg-white/[0.03] border border-white/10 p-4">
      <div className="flex items-start justify-between gap-3 mb-1">
        <div className="flex items-center gap-2 flex-wrap">
          <SourceLabel source={p.source} />
          <ConfBadge conf={p.confidence} />
          <span className="text-[10px] text-gray-500">{p.created_at.slice(0, 10)}</span>
        </div>
        <span className="text-[11px] text-amber-400 shrink-0">{daysLeft >= 0 ? `D-${daysLeft}` : '만료'}</span>
      </div>
      <p className="text-sm text-white leading-snug mb-1">{p.prediction}</p>
      <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
        <span className="font-medium text-gray-400">{p.target}</span>
        {p.target_code && <span className="text-gray-600 font-mono">{p.target_code}</span>}
        <DirBadge dir={p.direction} />
      </div>
      <PriceRow p={p} ws={ws} ts={ts} showCurrent />
      {ts.entry && <p className="text-[11px] text-gray-600 mt-1.5">진입: {ts.entry}</p>}
    </div>
  );
}

function fmtDateShort(utcStr: string | null): string {
  if (!utcStr) return '';
  try {
    const d = new Date(utcStr.replace(' ', 'T') + 'Z');
    return d.toLocaleString('ko-KR', { month: 'numeric', day: 'numeric', timeZone: 'Asia/Seoul' });
  } catch { return ''; }
}

function HitCard({ p, wsMap }: { p: PredictionRow; wsMap: Record<string, WsConsensus> }) {
  const ws = p.target_code ? (wsMap[p.target_code] ?? null) : null;
  const ts: TradeSetup = p.trade_setup ? JSON.parse(p.trade_setup) : {};
  const hitPct = p.hit_change_pct ?? p.price_change_pct;
  // 최고 수익이 있으면 그걸 메인 배지로, 날짜도 함께
  const displayPct = p.peak_change_pct ?? hitPct;
  const displayAt = p.peak_change_pct != null ? p.peak_at : null;
  return (
    <div className="rounded-2xl bg-emerald-500/5 border border-emerald-500/20 p-4">
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <SourceLabel source={p.source} />
          <span className="text-[10px] text-gray-500">{p.created_at.slice(0, 10)}</span>
        </div>
        <ResultBadge result={p.result} pct={displayPct} peakAt={displayAt} />
      </div>
      <p className="text-sm font-semibold text-white mb-2 leading-snug">{p.prediction}</p>
      <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
        <span className="font-medium text-gray-300">{p.target}</span>
        {p.target_code && <span className="text-gray-600 font-mono">{p.target_code}</span>}
        <DirBadge dir={p.direction} />
      </div>
      <PriceRow p={p} ws={ws} ts={ts} showCurrent />
      {p.basis && <p className="text-[11px] text-gray-500 mt-2 leading-relaxed">근거: {p.basis}</p>}
    </div>
  );
}

function MissCard({ p, wsMap }: { p: PredictionRow; wsMap: Record<string, WsConsensus> }) {
  const ws = p.target_code ? (wsMap[p.target_code] ?? null) : null;
  const ts: TradeSetup = p.trade_setup ? JSON.parse(p.trade_setup) : {};
  return (
    <div className="rounded-xl bg-white/[0.02] border border-white/5 p-4 opacity-70">
      <div className="flex items-start justify-between gap-3 mb-1">
        <div className="flex items-center gap-2 flex-wrap">
          <SourceLabel source={p.source} />
          <span className="text-[10px] text-gray-500">{p.created_at.slice(0, 10)}</span>
        </div>
        <ResultBadge result={p.result} pct={p.price_change_pct} />
      </div>
      <p className="text-sm text-gray-300 leading-snug mb-1">{p.prediction}</p>
      <div className="flex items-center gap-3 text-xs text-gray-500 mt-1 mb-2">
        <span>{p.target}</span>
        {p.target_code && <span className="text-gray-600 font-mono">{p.target_code}</span>}
        <DirBadge dir={p.direction} />
      </div>
      <PriceRow p={p} ws={ws} ts={ts} />
    </div>
  );
}

const PAGE_SIZE = 5;

export function ShowMorePredictions({
  initial,
  total,
  section,
  wsMap: initialWsMap,
}: {
  initial: PredictionRow[];
  total: number;
  section: 'hit' | 'pending' | 'miss';
  wsMap: Record<string, WsConsensus>;
}) {
  const [predictions, setPredictions] = useState(initial);
  const [wsMap, setWsMap] = useState(initialWsMap);
  const [isPending, startTransition] = useTransition();

  const hasMore = predictions.length < total;

  const loadMore = () => {
    startTransition(async () => {
      const res = await fetch(`/api/history?section=${section}&offset=${predictions.length}&limit=${PAGE_SIZE}`);
      if (!res.ok) return;
      const data = await res.json() as { predictions: PredictionRow[]; wsMap: Record<string, WsConsensus> };
      setPredictions(prev => [...prev, ...data.predictions]);
      setWsMap(prev => ({ ...prev, ...data.wsMap }));
    });
  };

  const Card = section === 'hit' ? HitCard : section === 'miss' ? MissCard : PendingCard;

  return (
    <>
      <div className={section === 'hit' ? 'space-y-3' : 'space-y-2'}>
        {predictions.map(p => <Card key={p.id} p={p} wsMap={wsMap} />)}
      </div>
      {hasMore && (
        <button
          onClick={loadMore}
          disabled={isPending}
          className="w-full mt-3 py-2.5 text-[12px] font-semibold text-gray-400 hover:text-gray-200 disabled:opacity-40 border border-white/[0.06] hover:border-white/[0.12] rounded-xl transition-colors"
        >
          {isPending ? '로딩 중...' : `더보기 (${total - predictions.length}건 남음) ▼`}
        </button>
      )}
    </>
  );
}
