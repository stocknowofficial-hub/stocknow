'use client';

import { useState, useRef, useEffect } from 'react';

export interface SourceEntry {
  source: string;
  date: string;
}

export interface TargetDisplay {
  displayName: string;
  target_code: string | null;
  up: number;
  down: number;
  count: number;
  dominant: string;
  keyPoints: string[];
  upSources: SourceEntry[];
  downSources: SourceEntry[];
}

const INITIAL = 5;
const PAGE_SIZE = 5;

function getSourceLabel(source: string): string {
  if (source.startsWith('briefing_kr')) return '🇰🇷 한국장 브리핑';
  if (source.startsWith('briefing_us')) return '🇺🇸 미국장 브리핑';
  return source;
}

function fmtDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${d.getMonth() + 1}/${d.getDate()}`;
}

function SourcePopup({ sources, onClose }: { sources: SourceEntry[]; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [onClose]);

  // source별로 날짜 그룹핑
  const grouped = new Map<string, string[]>();
  for (const { source, date } of sources) {
    const label = getSourceLabel(source);
    const existing = grouped.get(label) ?? [];
    const fmt = fmtDate(date);
    if (!existing.includes(fmt)) existing.push(fmt);
    grouped.set(label, existing);
  }

  return (
    <div
      ref={ref}
      className="absolute right-0 bottom-full mb-2 z-50 min-w-[160px] bg-[#1a1a1f] border border-white/15 rounded-xl px-3 py-2.5 shadow-2xl"
    >
      <p className="text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">분석 출처</p>
      <div className="space-y-1.5">
        {Array.from(grouped.entries()).map(([label, dates], i) => (
          <div key={i}>
            <p className="text-[11px] text-gray-200 font-medium">
              {label}
              <span className="text-gray-500 ml-1">({dates.join(', ')})</span>
            </p>
          </div>
        ))}
      </div>
      {/* 말풍선 꼬리 */}
      <div className="absolute right-3 top-full w-0 h-0 border-l-[5px] border-r-[5px] border-t-[5px] border-l-transparent border-r-transparent border-t-white/15" />
      <div className="absolute right-[13px] top-full w-0 h-0 border-l-[4px] border-r-[4px] border-t-[4px] border-l-transparent border-r-transparent border-t-[#1a1a1f]" />
    </div>
  );
}

function MentionBadge({ count, sources, color }: { count: number; sources: SourceEntry[]; color: string }) {
  const [open, setOpen] = useState(false);

  return (
    <span className="relative shrink-0 ml-2">
      <button
        onClick={() => setOpen(v => !v)}
        className={`${color} text-xs font-semibold hover:opacity-80 transition-opacity cursor-pointer`}
        title="클릭하면 분석 출처 확인"
      >
        {count}곳 언급 ▾
      </button>
      {open && sources.length > 0 && (
        <SourcePopup sources={sources} onClose={() => setOpen(false)} />
      )}
    </span>
  );
}

function TargetList({
  items,
  dir,
  total,
}: {
  items: TargetDisplay[];
  dir: 'up' | 'down';
  total: number;
}) {
  const [count, setCount] = useState(INITIAL);
  const visible = items.slice(0, count);
  const remaining = items.length - count;
  const countColor = dir === 'up' ? 'text-green-400' : 'text-red-400';
  const barClass =
    dir === 'up'
      ? 'bg-gradient-to-r from-green-500 to-emerald-400'
      : 'bg-gradient-to-r from-red-500 to-rose-400';

  return (
    <div className="space-y-2">
      {visible.map((t, i) => {
        const cnt = dir === 'up' ? t.up : t.down;
        const srcs = dir === 'up' ? t.upSources : t.downSources;
        return (
          <div key={i}>
            <div className="flex justify-between text-xs mb-1">
              <div className="flex items-center gap-1.5">
                <span className="text-gray-200 font-semibold">{t.displayName}</span>
                {t.target_code && t.target_code.length <= 6 && (
                  <span className="text-[10px] text-gray-600">{t.target_code}</span>
                )}
              </div>
              <MentionBadge count={cnt} sources={srcs} color={countColor} />
            </div>
            <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden mb-1.5">
              <div
                className={`h-full ${barClass} rounded-full`}
                style={{ width: `${Math.round((cnt / total) * 100)}%` }}
              />
            </div>
            {t.keyPoints.length > 0 && (
              <p className="text-[11px] text-gray-500 leading-relaxed">
                <span className="text-gray-600 font-semibold">근거</span>{' '}
                {t.keyPoints.map((kp, j) => `${j + 1}) ${kp}`).join('  ')}
              </p>
            )}
          </div>
        );
      })}
      {remaining > 0 && (
        <button
          onClick={() => setCount(c => c + PAGE_SIZE)}
          className="w-full py-2 text-[11px] text-gray-500 hover:text-gray-300 border border-white/[0.06] hover:border-white/[0.12] rounded-xl transition-colors mt-1"
        >
          더보기 ({Math.min(PAGE_SIZE, remaining)}개 · 총 {remaining}개 남음) ▼
        </button>
      )}
    </div>
  );
}

export function ShowMoreTargets({
  bullish,
  bearish,
  sideways,
  total,
}: {
  bullish: TargetDisplay[];
  bearish: TargetDisplay[];
  sideways: TargetDisplay[];
  total: number;
}) {
  return (
    <>
      {bullish.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-bold text-green-400 mb-2">📈 강세 전망</p>
          <TargetList items={bullish} dir="up" total={total} />
        </div>
      )}
      {bearish.length > 0 && (
        <div className="mb-4">
          <p className="text-[11px] font-bold text-red-400 mb-2">📉 약세 전망</p>
          <TargetList items={bearish} dir="down" total={total} />
        </div>
      )}
      {sideways.length > 0 && (
        <div>
          <p className="text-[11px] font-bold text-gray-500 mb-2">→ 방향 혼재</p>
          <div className="flex flex-wrap gap-2">
            {sideways.map((t, i) => (
              <span
                key={i}
                className="text-[11px] text-gray-500 bg-white/5 px-2 py-1 rounded-lg"
              >
                {t.displayName} ({t.count}건)
              </span>
            ))}
          </div>
        </div>
      )}
    </>
  );
}
