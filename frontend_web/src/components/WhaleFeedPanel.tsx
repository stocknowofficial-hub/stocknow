'use client';

import { useState } from 'react';

interface StockItem {
  name: string;
  code: string;
  price: number;
  chgrate: string;
  amount_eok?: number;
  acml_vol?: number;
  is_header?: boolean;
}

export interface Sections {
  program: StockItem[];
  foreign: StockItem[];
  volume: StockItem[];
}

interface TabConfig {
  key: 'program' | 'foreign' | 'volume';
  label: string;
}

interface WhaleFeedPanelProps {
  sections: Sections | null;
  updated_at: string | null;
  tabs?: TabConfig[];
  emptyMessage?: string;
}

const KR_TABS: TabConfig[] = [
  { key: 'volume', label: '📈 거래량' },
  { key: 'foreign', label: '👽 외국인' },
  { key: 'program', label: '🏛️ 기관' },
];

const US_TABS: TabConfig[] = [
  { key: 'volume',  label: '📊 거래량 Top10' },
  { key: 'program', label: '📊 지수/Big7' },
  { key: 'foreign', label: '🌍 섹터' },
];

export { KR_TABS, US_TABS };

export function WhaleFeedPanel({ sections, updated_at, tabs = KR_TABS, emptyMessage }: WhaleFeedPanelProps) {
  const [tab, setTab] = useState<'program' | 'foreign' | 'volume'>(tabs[0].key);
  const [showAll, setShowAll] = useState(false);

  if (!sections) {
    return (
      <div className="text-center py-10 text-gray-600 text-sm">
        {emptyMessage ?? '아직 수급 데이터가 없습니다.'}<br />
        <span className="text-xs">장 중에 자동으로 업데이트됩니다.</span>
      </div>
    );
  }

  const items = sections[tab] ?? [];

  return (
    <div>
      {/* 탭 */}
      <div className="flex gap-1 mb-4 bg-white/[0.03] rounded-xl p-1">
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => { setTab(key); setShowAll(false); }}
            className={`flex-1 py-1.5 rounded-lg text-xs font-semibold transition-all ${tab === key
              ? 'bg-white/10 text-white'
              : 'text-gray-500 hover:text-gray-300'
              }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* 종목 리스트 */}
      <div className="space-y-1.5 cursor-default">
        {(() => {
          const limit = tab === 'volume' ? (showAll ? 20 : 10) : 20;
          let rank = 0;
          return items.slice(0, limit).map((item, i) => {
            if (item.is_header) {
              rank = 0; // reset rank for the new section
              return (
                <div key={i} className={`px-2 text-sm font-bold text-white/90 ${i === 0 ? 'mb-2' : 'mt-5 mb-2'}`}>
                  {item.name}
                </div>
              );
            }
            rank++;
            const rate = parseFloat(item.chgrate ?? '0');
            const isUp = rate > 0;
            const isDown = rate < 0;
            return (
              <div key={i} className="flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-white/[0.03] transition-colors">
                <span className="text-xs text-gray-600 w-4 shrink-0">{rank}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium text-white truncate">{item.name}</span>
                    <span className={`text-xs font-bold shrink-0 ${isUp ? 'text-red-400' : isDown ? 'text-blue-400' : 'text-gray-400'}`}>
                      {isUp ? '+' : ''}{rate.toFixed(2)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-2 mt-0.5">
                    <span className="text-[10px] text-gray-600">{item.code}</span>
                    {item.acml_vol != null && item.acml_vol > 0 ? (
                      <span className="text-[10px] text-gray-500 shrink-0">
                        거래주식 수 {Math.round(item.acml_vol / 10000).toLocaleString()}만주
                      </span>
                    ) : item.amount_eok != null ? (
                      <span className={`text-[10px] shrink-0 ${item.amount_eok >= 0 ? 'text-gray-500' : 'text-blue-400'}`}>
                        {item.amount_eok >= 0 ? '순매수' : '순매도'} {Math.abs(item.amount_eok).toFixed(1)}억
                      </span>
                    ) : null}
                  </div>
                </div>
              </div>
            );
          });
        })()}
      </div>

      {/* 더보기 버튼 — 거래량 탭에서 10개 이상일 때만 */}
      {tab === 'volume' && items.length > 10 && (
        <button
          onClick={() => setShowAll(v => !v)}
          className="w-full mt-3 py-2 rounded-xl text-xs font-semibold text-gray-500 hover:text-gray-300 bg-white/[0.03] hover:bg-white/[0.06] transition-all"
        >
          {showAll ? '▲ 접기' : `▼ 더보기`}
        </button>
      )}

    </div>
  );
}
