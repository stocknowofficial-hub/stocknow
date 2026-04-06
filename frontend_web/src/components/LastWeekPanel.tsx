'use client';

import { useState } from 'react';

interface TargetEntry {
  name: string;
  count: number;
  thisCount: number;
}

interface Props {
  lastBullish: TargetEntry[];
  lastBearish: TargetEntry[];
}

function Trend({ thisCount, lastCount }: { thisCount: number; lastCount: number }) {
  if (lastCount === 0) return <span className="text-[10px] text-blue-400 font-bold">NEW</span>;
  if (thisCount > lastCount) return <span className="text-[10px] text-emerald-400 font-bold">▲{thisCount - lastCount}</span>;
  if (thisCount < lastCount) return <span className="text-[10px] text-rose-400 font-bold">▼{lastCount - thisCount}</span>;
  return <span className="text-[10px] text-gray-500">—</span>;
}

export function LastWeekPanel({ lastBullish, lastBearish }: Props) {
  const [open, setOpen] = useState(false);

  if (lastBullish.length === 0 && lastBearish.length === 0) return null;

  return (
    <div className="mt-4 border-t border-white/[0.06] pt-4">
      <button
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        <span>{open ? '▲' : '▼'}</span>
        <span>지난 주 컨센서스 {open ? '접기' : '확인하기'}</span>
      </button>

      {open && (
        <div className="mt-4 space-y-4">
          {lastBullish.length > 0 && (
            <div>
              <p className="text-[11px] font-bold text-green-400/70 mb-2">📈 지난 주 강세</p>
              <div className="space-y-2">
                {lastBullish.map(t => (
                  <div key={t.name} className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">{t.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500">{t.count}곳</span>
                      <span className="text-gray-600">→</span>
                      <span className={t.thisCount > 0 ? 'text-green-400' : 'text-gray-500'}>이번 주 {t.thisCount}곳</span>
                      <Trend thisCount={t.thisCount} lastCount={t.count} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {lastBearish.length > 0 && (
            <div>
              <p className="text-[11px] font-bold text-red-400/70 mb-2">📉 지난 주 약세</p>
              <div className="space-y-2">
                {lastBearish.map(t => (
                  <div key={t.name} className="flex items-center justify-between text-xs">
                    <span className="text-gray-400">{t.name}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500">{t.count}곳</span>
                      <span className="text-gray-600">→</span>
                      <span className={t.thisCount > 0 ? 'text-rose-400' : 'text-gray-500'}>이번 주 {t.thisCount}곳</span>
                      <Trend thisCount={t.thisCount} lastCount={t.count} />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
