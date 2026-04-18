'use client';
import { useState, useMemo } from 'react';

export interface TableRow {
  id: string;
  source: string;
  source_desc: string | null;
  source_url: string | null;
  target: string;
  target_code: string | null;
  direction: 'up' | 'down' | 'sideways';
  confidence: 'high' | 'medium' | 'low';
  action: string | null;
  expires_at: string;
  created_at: string;
}

const ETF_NAMES: Record<string, string> = {
  '069500': 'KODEX 200',
  '379800': 'KODEX S&P500',
  '133690': 'TIGER 나스닥100',
  '261220': 'KODEX WTI원유',
  '091160': 'KODEX 반도체',
  '228800': 'KODEX 금선물',
  '102110': 'TIGER 200',
  '122630': 'KODEX 레버리지',
  '114800': 'KODEX 인버스',
  '411060': 'ACE 미국나스닥100',
  '360750': 'TIGER 미국S&P500',
};

const CONF_RANK: Record<string, number> = { high: 3, medium: 2, low: 1 };
const PAGE_SIZE = 10;

function getShortName(target: string, code: string | null): string {
  if (code && ETF_NAMES[code]) return ETF_NAMES[code];
  if (target && !/^\d+$/.test(target)) return target;
  return target || code || '-';
}

function daysLeft(expiresAt: string): number {
  const diff = new Date(expiresAt).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

// "매수 고려 · 이란 전쟁..." → "매수 고려"
function getActionType(action: string | null): string | null {
  if (!action) return null;
  return action.split('·')[0].trim();
}

function getSourceLabel(source: string, sourceDesc: string | null): string {
  if (sourceDesc) {
    const m = sourceDesc.match(/^\[?([^\]]+증권|BlackRock|키움|[A-Za-z]+투자[^\]]*|[A-Za-z]+)\]?/);
    if (m) return m[1].trim();
  }
  const MAP: Record<string, string> = {
    blackrock: 'BlackRock', kiwoom: '키움증권', hana: '하나증권',
    hanwha: '한화투자증권', mirae: '미래에셋', samsung: '삼성증권',
    shinhan: '신한투자증권', kb: 'KB증권', nh: 'NH투자증권',
    briefing: '시황브리핑', report: '리포트',
  };
  return MAP[source] ?? source;
}

type DirFilter  = 'all' | 'up' | 'down';
type ConfFilter = 'all' | 'high' | 'medium' | 'low';
type DdayFilter = 'all' | '7' | '14';

export function PredictionTableSection({ rows }: { rows: TableRow[] }) {
  const [dirFilter,  setDirFilter]  = useState<DirFilter>('all');
  const [confFilter, setConfFilter] = useState<ConfFilter>('all');
  const [ddayFilter, setDdayFilter] = useState<DdayFilter>('all');
  const [showCount,  setShowCount]  = useState(PAGE_SIZE);

  // 필터 후 신뢰도→최신순 정렬
  const filtered = useMemo(() => {
    return rows
      .filter(r => {
        if (dirFilter  !== 'all' && r.direction  !== dirFilter)  return false;
        if (confFilter !== 'all' && r.confidence !== confFilter) return false;
        if (ddayFilter !== 'all') {
          const d = daysLeft(r.expires_at);
          if (ddayFilter === '7'  && d > 7)  return false;
          if (ddayFilter === '14' && d > 14) return false;
        }
        return true;
      })
      .sort((a, b) => {
        const cd = (CONF_RANK[b.confidence] ?? 0) - (CONF_RANK[a.confidence] ?? 0);
        if (cd !== 0) return cd;
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
      });
  }, [rows, dirFilter, confFilter, ddayFilter]);

  // 필터 변경 시 표시 수 리셋
  const handleFilter = <T,>(setter: (v: T) => void) => (v: T) => {
    setter(v);
    setShowCount(PAGE_SIZE);
  };

  const visible   = filtered.slice(0, showCount);
  const remaining = filtered.length - showCount;

  // 아래 리포트 섹션으로 스크롤
  const scrollToReports = () => {
    const el = document.getElementById('reports-section');
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  function FilterBtn<T extends string>({
    value, current, set, label, activeClass,
  }: { value: T; current: T; set: (v: T) => void; label: string; activeClass?: string }) {
    return (
      <button
        onClick={() => set(value)}
        className={`text-[11px] px-2.5 py-1 rounded-lg font-medium transition-colors ${
          value === current
            ? (activeClass ?? 'bg-white/15 text-white')
            : 'bg-white/[0.04] text-gray-500 hover:text-gray-300 hover:bg-white/[0.07]'
        }`}
      >
        {label}
      </button>
    );
  }

  return (
    <div>
      {/* 필터 */}
      <div className="flex flex-wrap gap-x-3 gap-y-2 mb-4">
        <div className="flex gap-1">
          <FilterBtn value="all"  current={dirFilter}  set={handleFilter(setDirFilter)}  label="전체" />
          <FilterBtn value="up"   current={dirFilter}  set={handleFilter(setDirFilter)}  label="📈 매수" activeClass="bg-emerald-500/20 text-emerald-400" />
          <FilterBtn value="down" current={dirFilter}  set={handleFilter(setDirFilter)}  label="📉 매도" activeClass="bg-rose-500/20 text-rose-400" />
        </div>
        <div className="flex gap-1">
          <FilterBtn value="all"    current={confFilter} set={handleFilter(setConfFilter)} label="전체" />
          <FilterBtn value="high"   current={confFilter} set={handleFilter(setConfFilter)} label="HIGH" activeClass="bg-red-500/20 text-red-400" />
          <FilterBtn value="medium" current={confFilter} set={handleFilter(setConfFilter)} label="MED"  activeClass="bg-amber-500/20 text-amber-400" />
          <FilterBtn value="low"    current={confFilter} set={handleFilter(setConfFilter)} label="LOW"  activeClass="bg-white/10 text-gray-400" />
        </div>
        <div className="flex gap-1">
          <FilterBtn value="all" current={ddayFilter} set={handleFilter(setDdayFilter)} label="전체" />
          <FilterBtn value="7"   current={ddayFilter} set={handleFilter(setDdayFilter)} label="⏰ 7일 이내"  activeClass="bg-amber-500/20 text-amber-400" />
          <FilterBtn value="14"  current={ddayFilter} set={handleFilter(setDdayFilter)} label="14일 이내" activeClass="bg-white/10 text-gray-400" />
        </div>
      </div>

      <p className="text-[11px] text-gray-600 mb-3">{filtered.length}건 중 {visible.length}건 표시</p>

      {filtered.length === 0 ? (
        <p className="text-center text-sm text-gray-600 py-6">해당 조건의 예측이 없습니다.</p>
      ) : (
        <>
          <div className="space-y-1.5">
            {visible.map(r => {
              const d = daysLeft(r.expires_at);
              const dColor = d <= 3 ? 'text-rose-400' : d <= 7 ? 'text-amber-400' : 'text-gray-500';
              const dBg    = d <= 3 ? 'bg-rose-500/10'  : d <= 7 ? 'bg-amber-500/10' : 'bg-white/[0.04]';
              const confColor = r.confidence === 'high' ? 'text-red-400' : r.confidence === 'medium' ? 'text-amber-400' : 'text-gray-500';
              const dirIcon   = r.direction === 'up' ? '↑' : r.direction === 'down' ? '↓' : '→';
              const dirBg     = r.direction === 'up' ? 'bg-emerald-500/15 text-emerald-400' : r.direction === 'down' ? 'bg-rose-500/15 text-rose-400' : 'bg-white/[0.05] text-gray-400';
              const actionBg  = r.direction === 'up' ? 'bg-emerald-500/10 text-emerald-400' : r.direction === 'down' ? 'bg-rose-500/10 text-rose-400' : 'bg-white/[0.05] text-gray-400';
              const name      = getShortName(r.target, r.target_code);
              const srcLabel  = getSourceLabel(r.source, r.source_desc);
              const actionType = getActionType(r.action);
              const dateLabel = (() => {
                const d = new Date(r.created_at);
                return `${d.getMonth() + 1}/${d.getDate()}`;
              })();

              return (
                <button
                  key={r.id}
                  onClick={scrollToReports}
                  className="w-full text-left"
                >
                  <div className="flex items-center gap-2 px-3 py-2.5 rounded-xl bg-white/[0.03] hover:bg-white/[0.08] active:bg-white/[0.12] transition-colors cursor-pointer">
                    {/* 날짜 */}
                    <span className="text-[10px] text-gray-600 shrink-0 w-7 font-mono">{dateLabel}</span>
                    {/* 방향 */}
                    <span className={`text-[11px] font-bold px-1.5 py-0.5 rounded-md shrink-0 ${dirBg}`}>{dirIcon}</span>
                    {/* 종목명 + 티커 */}
                    <span className="flex items-center gap-1.5 flex-1 min-w-0">
                      <span className="text-xs font-semibold text-gray-200 truncate">{name}</span>
                      {r.target_code && <span className="text-[10px] text-gray-600 font-mono shrink-0">{r.target_code}</span>}
                    </span>
                    {/* 액션 타입 — sm 이상에서만 표시 */}
                    {actionType && (
                      <span className={`text-[10px] px-2 py-0.5 rounded-md shrink-0 hidden sm:inline-block ${actionBg}`}>
                        ⚡ {actionType}
                      </span>
                    )}
                    {/* 신뢰도 */}
                    <span className={`text-[10px] font-bold shrink-0 ${confColor}`}>
                      {r.confidence.toUpperCase()}
                    </span>
                    {/* D-day */}
                    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded-md shrink-0 ${dBg} ${dColor}`}>
                      D-{d}
                    </span>
                    {/* 증권사 */}
                    <span className="text-[10px] text-gray-500 shrink-0 max-w-[60px] truncate">{srcLabel}</span>
                    {/* 리포트 이동 힌트 */}
                    <span className="text-[10px] text-gray-700 shrink-0">↓</span>
                  </div>
                </button>
              );
            })}
          </div>

          {/* 더보기 버튼 */}
          {remaining > 0 && (
            <button
              onClick={() => setShowCount(c => c + PAGE_SIZE)}
              className="mt-3 w-full py-2.5 rounded-xl border border-white/10 text-[12px] text-gray-400 hover:text-white hover:border-white/20 hover:bg-white/[0.04] transition-colors"
            >
              더보기 ({remaining}건 남음) ▼
            </button>
          )}

          <p className="text-[10px] text-gray-700 mt-3 text-right">
            클릭하면 아래 상세 리포트로 이동합니다
          </p>
        </>
      )}
    </div>
  );
}
