'use client';

import { useState } from 'react';

export interface TrumpPrediction {
  id: string;
  source_desc: string | null;
  source_url: string | null;
  prediction: string | null;
  direction: string;
  target: string | null;
  target_code: string | null;
  confidence: string;
  key_points: string | null;
  created_at: string;
  expires_at: string | null;
  result: string | null;
  entry_price: number | null;
  current_price: number | null;
  price_change_pct: number | null;
}

function DirIcon({ dir }: { dir: string }) {
  if (dir === 'up') return <span className="font-bold text-emerald-400">↑</span>;
  if (dir === 'down') return <span className="font-bold text-rose-400">↓</span>;
  return <span className="text-gray-400">→</span>;
}

function ConfBadge({ conf }: { conf: string }) {
  const upper = (conf ?? '').toUpperCase();
  if (upper === 'HIGH') return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20">HIGH</span>;
  if (upper === 'MEDIUM') return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/20">MEDIUM</span>;
  return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/10 text-gray-500">LOW</span>;
}

function ResultBadge({ result }: { result: string }) {
  if (result === 'hit') return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">✅ 적중</span>;
  if (result === 'miss') return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20">❌ 빗나감</span>;
  return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/5 text-gray-400 border border-white/10">보류</span>;
}

function formatDate(str: string) {
  // UTC → 미국 동부시간(ET) 변환
  const d = new Date(str + 'Z');
  const utcMs = d.getTime();
  const year = d.getUTCFullYear();
  // 3월 두 번째 일요일 02:00 ET = 07:00 UTC
  const mar1 = Date.UTC(year, 2, 1);
  const mar1dow = new Date(mar1).getUTCDay();
  const dstStart = mar1 + ((7 - mar1dow) % 7 + 7) * 86400000 + 7 * 3600000;
  // 11월 첫 번째 일요일 02:00 ET = 06:00 UTC
  const nov1 = Date.UTC(year, 10, 1);
  const nov1dow = new Date(nov1).getUTCDay();
  const dstEnd = nov1 + ((7 - nov1dow) % 7) * 86400000 + 6 * 3600000;
  const isDST = utcMs >= dstStart && utcMs < dstEnd;
  const etOffset = isDST ? -4 : -5;
  const label = isDST ? 'EDT' : 'EST';
  const et = new Date(utcMs + etOffset * 3600000);
  const yy = et.getUTCFullYear();
  const mo = String(et.getUTCMonth() + 1).padStart(2, '0');
  const dd = String(et.getUTCDate()).padStart(2, '0');
  const hh = String(et.getUTCHours()).padStart(2, '0');
  const mm = String(et.getUTCMinutes()).padStart(2, '0');
  return `${yy}-${mo}-${dd} ${label} ${hh}:${mm}`;
}

function DaysLeft({ expires }: { expires: string | null }) {
  if (!expires) return null;
  const diff = Math.ceil((new Date(expires).getTime() - Date.now()) / 86400000);
  if (diff < 0) return <span className="text-[10px] text-gray-600">만료</span>;
  return <span className="text-[10px] text-gray-500">D-{diff}</span>;
}

function TrumpCard({ p }: { p: TrumpPrediction }) {
  const points = p.key_points ? (() => { try { return JSON.parse(p.key_points!); } catch { return null; } })() : null;
  const hasPriceChange = p.price_change_pct !== null && p.price_change_pct !== undefined;
  const isAligned = hasPriceChange && (
    (p.direction === 'up' && (p.price_change_pct ?? 0) > 0) ||
    (p.direction === 'down' && (p.price_change_pct ?? 0) < 0)
  );

  if (p.result !== null) {
    // 결과 확정 카드 (compact)
    return (
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <DirIcon dir={p.direction} />
            <span className="text-sm text-gray-300">{p.prediction}</span>
          </div>
          <ResultBadge result={p.result} />
        </div>
        <div className="flex items-center justify-between">
          <p className="text-[11px] text-gray-600">{p.source_desc || `Trump Truth Social · ${formatDate(p.created_at)}`}</p>
          {p.source_url && (
            <a href={p.source_url} target="_blank" rel="noopener noreferrer"
              className="text-[11px] text-gray-600 hover:text-gray-400">원문 →</a>
          )}
        </div>
      </div>
    );
  }

  // 진행 중 카드
  return (
    <div className={`rounded-2xl border p-5 ${isAligned ? 'border-emerald-500/20 bg-emerald-500/5' : 'border-white/5 bg-white/[0.02]'}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-orange-400">🏛️ 트럼프</span>
          <ConfBadge conf={p.confidence} />
        </div>
        <DaysLeft expires={p.expires_at} />
      </div>

      <div className="flex items-center gap-2 mb-2">
        <DirIcon dir={p.direction} />
        {p.prediction && <p className="text-sm font-semibold text-white">{p.prediction}</p>}
      </div>

      {points && Array.isArray(points) && points.length > 0 && (
        <ul className="space-y-1 mb-3">
          {points.map((pt: string, i: number) => (
            <li key={i} className="flex items-start gap-2 text-xs text-gray-400">
              <span className="text-gray-600 mt-0.5 shrink-0">•</span>
              <span>{pt}</span>
            </li>
          ))}
        </ul>
      )}

      {hasPriceChange && (
        <div className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-lg mb-2 ${isAligned ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-white/5 text-gray-500 border border-white/10'}`}>
          {isAligned ? '✅' : '⏳'} 게시 당시 대비 {(p.price_change_pct ?? 0) >= 0 ? '+' : ''}{(p.price_change_pct ?? 0).toFixed(2)}%
          {p.target && <span className="text-gray-500 ml-1">({p.target})</span>}
        </div>
      )}

      <div className="flex items-center justify-between mt-2">
        <p className="text-[11px] text-gray-600">{p.source_desc || `Trump Truth Social · ${formatDate(p.created_at)}`}</p>
        {p.source_url && (
          <a href={p.source_url} target="_blank" rel="noopener noreferrer"
            className="text-[11px] text-gray-600 hover:text-gray-400">원문 →</a>
        )}
      </div>
    </div>
  );
}

const PAGE_SIZE = 20;

export function TrumpFeed({ initialPosts }: { initialPosts: TrumpPrediction[] }) {
  const [posts, setPosts] = useState<TrumpPrediction[]>(initialPosts);
  const [loading, setLoading] = useState(false);
  const [hasMore, setHasMore] = useState(initialPosts.length === PAGE_SIZE);

  async function loadMore() {
    setLoading(true);
    try {
      const res = await fetch(`/api/predictions?source=trump&limit=${PAGE_SIZE}&offset=${posts.length}`);
      const data = await res.json();
      const newPosts: TrumpPrediction[] = data.predictions ?? [];
      setPosts(prev => [...prev, ...newPosts]);
      setHasMore(newPosts.length === PAGE_SIZE);
    } catch {
      // 네트워크 오류 시 조용히 실패
    } finally {
      setLoading(false);
    }
  }

  const pending = posts.filter(p => p.result === null);
  const completed = posts.filter(p => p.result !== null);

  return (
    <>
      {/* 진행 중 */}
      {pending.length > 0 && (
        <section className="rounded-2xl lg:rounded-3xl border border-white/10 bg-white/[0.03] p-6 lg:p-8 mb-6">
          <div className="mb-4">
            <h3 className="text-base font-bold text-white">⏳ 진행 중 ({pending.length})</h3>
            <p className="text-[10px] text-gray-500 mt-0.5">시장 결과를 기다리고 있는 예측</p>
          </div>
          <div className="space-y-4">
            {pending.map(p => <TrumpCard key={p.id} p={p} />)}
          </div>
        </section>
      )}

      {/* 결과 확정 */}
      {completed.length > 0 && (
        <section className="rounded-2xl lg:rounded-3xl border border-white/10 bg-white/[0.03] p-6 lg:p-8 mb-6">
          <div className="mb-4">
            <h3 className="text-base font-bold text-white">🎯 결과 확정 ({completed.length})</h3>
            <p className="text-[10px] text-gray-500 mt-0.5">최근 종료된 예측의 적중 여부</p>
          </div>
          <div className="space-y-3">
            {completed.map(p => <TrumpCard key={p.id} p={p} />)}
          </div>
        </section>
      )}

      {/* 더보기 버튼 */}
      {hasMore && (
        <button
          onClick={loadMore}
          disabled={loading}
          className="w-full py-3 rounded-2xl text-sm font-semibold text-gray-400 hover:text-white bg-white/[0.03] hover:bg-white/[0.06] border border-white/[0.06] transition-all disabled:opacity-50"
        >
          {loading ? '불러오는 중...' : '▼ 더보기'}
        </button>
      )}
    </>
  );
}
