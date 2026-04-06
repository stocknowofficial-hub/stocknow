'use client';

import { useState } from 'react';

interface RelatedStock {
  name: string;
  code: string;
  role?: string;
  reason: string;
}

interface TradeSetup {
  entry?: string;
  stop_loss?: string;
  target?: string;
}

interface WallStreetData {
  recommendation: string;
  target_price: number | null;
  current_price: number | null;
  analyst_count: number;
  upside_pct: number | null;
}

interface ReportItem {
  id: string;
  source: string;
  source_desc: string | null;
  source_url: string | null;
  prediction: string;
  direction: string;
  target: string;
  target_code: string | null;
  confidence: string;
  created_at: string;
  key_points: string | null;
  related_stocks: string | null;
  action: string | null;
  trade_setup: string | null;
  price_change_pct: number | null;
  expires_at: string | null;
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
  return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/5 text-gray-500 border border-white/10">LOW</span>;
}

function DaysLeft({ expires }: { expires: string | null }) {
  if (!expires) return null;
  const diff = Math.ceil((new Date(expires).getTime() - Date.now()) / 86400000);
  if (diff < 0) return <span className="text-[10px] text-gray-600">만료</span>;
  return <span className="text-[10px] text-gray-500">D-{diff}</span>;
}

function ActionBadge({ action, target }: { action: string; target?: string }) {
  const label = action.split(' · ')[0].trim();
  const reason = action.includes(' · ') ? action.slice(action.indexOf(' · ') + 3) : null;

  let bg = 'bg-gray-500/20 border-white/10'; let text = 'text-gray-400';
  if (label === '매수 고려' || label === '비중 확대') { bg = 'bg-emerald-500/10 border-emerald-500/20'; text = 'text-emerald-400'; }
  else if (label === '매도 고려' || label === '비중 축소') { bg = 'bg-rose-500/10 border-rose-500/20'; text = 'text-rose-400'; }
  else if (label === '관망') { bg = 'bg-amber-500/10 border-amber-500/20'; text = 'text-amber-400'; }

  return (
    <div className={`flex flex-col gap-0.5 px-3 py-2.5 rounded-xl border ${bg}`}>
      <span className={`text-sm font-bold ${text}`}>
        ⚡ {target ? `${target} ` : ''}{label}
      </span>
      {reason && <span className={`text-[11px] ${text} opacity-70`}>{reason}</span>}
    </div>
  );
}

function RoleBadge({ role }: { role?: string }) {
  if (!role) return null;
  if (role === '매수') return <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">매수</span>;
  if (role === '매도') return <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-rose-500/10 text-rose-400 border border-rose-500/20">매도</span>;
  if (role === '헤지') return <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20">헤지</span>;
  return null;
}

function fmtTargetPrice(code: string | null, price: number): string {
  if (code && /^\d{6}$/.test(code)) return `${Math.round(price).toLocaleString()}원`;
  return `$${price.toFixed(0)}`;
}

function WsBadge({ ws, targetCode }: { ws: WallStreetData; targetCode: string | null }) {
  const recColor =
    ws.recommendation === 'Strong Buy' ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' :
    ws.recommendation === 'Buy' ? 'text-emerald-300 bg-emerald-500/8 border-emerald-500/20' :
    ws.recommendation === 'Hold' ? 'text-amber-400 bg-amber-500/10 border-amber-500/30' :
    'text-rose-400 bg-rose-500/10 border-rose-500/30';
  const upsideColor = ws.upside_pct && ws.upside_pct > 0 ? 'text-emerald-400' : 'text-rose-400';

  return (
    <div className="mt-1 flex items-center gap-2 flex-wrap">
      <span className="text-[9px] text-blue-400 font-bold bg-blue-500/10 border border-blue-500/20 px-1.5 py-0.5 rounded">🏦 컨센서스</span>
      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border ${recColor}`}>{ws.recommendation}</span>
      {ws.target_price && (
        <span className={`text-[9px] font-mono ${upsideColor}`}>
          목표 {fmtTargetPrice(targetCode, ws.target_price)}
          {ws.upside_pct !== null && ` (${ws.upside_pct > 0 ? '+' : ''}${ws.upside_pct}%)`}
        </span>
      )}
      {ws.analyst_count > 0 && <span className="text-[9px] text-gray-600">{ws.analyst_count}명 커버리지</span>}
    </div>
  );
}

function AccordionItem({ r, wsMap }: { r: ReportItem; wsMap: Record<string, WallStreetData> }) {
  const [open, setOpen] = useState(false);
  const points: string[] | null = r.key_points ? (() => { try { return JSON.parse(r.key_points!); } catch { return null; } })() : null;
  const relatedStocks: RelatedStock[] | null = r.related_stocks ? (() => { try { return JSON.parse(r.related_stocks!); } catch { return null; } })() : null;
  const tradeSetup: TradeSetup | null = r.trade_setup ? (() => { try { return JSON.parse(r.trade_setup!); } catch { return null; } })() : null;
  const hasPriceChange = r.price_change_pct !== null && r.price_change_pct !== undefined;
  const isAligned = hasPriceChange && (
    (r.direction === 'up' && (r.price_change_pct ?? 0) > 0) ||
    (r.direction === 'down' && (r.price_change_pct ?? 0) < 0)
  );

  return (
    <div className="border-b border-white/[0.04] last:border-0">
      {/* 헤더 행 */}
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-start gap-3 py-3 text-left hover:bg-white/[0.02] transition-colors rounded-lg px-1 -mx-1"
      >
        <div className="mt-0.5 w-5 shrink-0 text-center">
          <DirIcon dir={r.direction} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5 flex-wrap">
            <span className="text-xs font-semibold text-gray-300">{r.source}</span>
            <ConfBadge conf={r.confidence} />
            <span className="text-[10px] text-gray-600">
              {(() => { const d = new Date(r.created_at); return `${d.getMonth()+1}/${d.getDate()}`; })()}
            </span>
            <DaysLeft expires={r.expires_at} />
            {/* 접힌 상태에서 action 배지 미리 표시 */}
            {!open && r.action && (() => {
              const label = r.action.split(' · ')[0].trim();
              let cls = 'bg-gray-500/10 text-gray-400 border-white/10';
              if (label === '매수 고려' || label === '비중 확대') cls = 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
              else if (label === '매도 고려' || label === '비중 축소') cls = 'bg-rose-500/10 text-rose-400 border-rose-500/20';
              else if (label === '관망') cls = 'bg-amber-500/10 text-amber-400 border-amber-500/20';
              return <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${cls}`}>⚡ {label}</span>;
            })()}
          </div>
          <p className="text-sm text-white leading-snug line-clamp-1">{r.prediction}</p>
          {!open && (
            <p className="text-[11px] text-gray-500 mt-0.5 truncate">{r.source_desc || r.target}</p>
          )}
        </div>
        <span className="text-gray-600 text-xs shrink-0 mt-1">{open ? '▲' : '▼'}</span>
      </button>

      {/* 펼침 내용 */}
      {open && (
        <div className="pb-4 px-8 space-y-3">

          {/* 예측 요약 — 컨텍스트 제공 */}
          <p className="text-sm font-semibold text-white leading-snug">{r.prediction}</p>

          {/* 핵심 근거 */}
          {points && Array.isArray(points) && points.length > 0 && (
            <ul className="space-y-1.5">
              {points.map((pt: string, i: number) => (
                <li key={i} className="flex items-start gap-2 text-xs text-gray-400">
                  <span className="text-gray-600 mt-0.5 shrink-0">•</span>
                  <span>{pt}</span>
                </li>
              ))}
            </ul>
          )}

          {/* Action 추천 + Trade Setup */}
          {r.action && <ActionBadge action={r.action} target={r.target || undefined} />}
          {tradeSetup && (tradeSetup.entry || tradeSetup.stop_loss || tradeSetup.target) && (
            <div className="grid grid-cols-3 gap-2 text-center">
              {tradeSetup.entry && (
                <div className="bg-white/[0.04] rounded-xl px-2 py-2.5">
                  <p className="text-[9px] font-bold text-gray-500 uppercase tracking-wider mb-1">진입</p>
                  <p className="text-[11px] text-gray-300 leading-tight line-clamp-2">{tradeSetup.entry}</p>
                </div>
              )}
              {tradeSetup.stop_loss && (
                <div className="bg-rose-500/[0.07] rounded-xl px-2 py-2.5">
                  <p className="text-[9px] font-bold text-rose-500/70 uppercase tracking-wider mb-1">손절</p>
                  <p className="text-[11px] text-rose-400 leading-tight line-clamp-2">{tradeSetup.stop_loss}</p>
                </div>
              )}
              {tradeSetup.target && (
                <div className="bg-emerald-500/[0.07] rounded-xl px-2 py-2.5">
                  <p className="text-[9px] font-bold text-emerald-500/70 uppercase tracking-wider mb-1">목표</p>
                  <p className="text-[11px] text-emerald-400 leading-tight line-clamp-2">{tradeSetup.target}</p>
                </div>
              )}
            </div>
          )}

          {/* 관련 종목 */}
          {relatedStocks && relatedStocks.length > 0 && (
            <div>
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">함께 볼 종목 (참고용)</p>
              <div className="space-y-2">
                {relatedStocks.map((s, i) => {
                  const isKr = /^\d{6}$/.test(s.code);
                  const href = isKr
                    ? `https://finance.naver.com/item/main.naver?code=${s.code}`
                    : `https://finance.naver.com/world/sise.naver?symbol=${s.code}`;
                  const ws = wsMap[s.code?.toUpperCase()];
                  return (
                    <div key={i} className="flex items-start gap-2">
                      <RoleBadge role={s.role} />
                      <div className="flex-1 min-w-0">
                        <a href={href} target="_blank" rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 hover:opacity-80 transition-opacity">
                          <span className="text-xs font-semibold text-gray-200">{s.name}</span>
                          <span className="text-[10px] text-gray-600">{s.code}</span>
                        </a>
                        <p className="text-[10px] text-gray-500 mt-0.5">{s.reason}</p>
                        {ws && <WsBadge ws={ws} targetCode={s.code} />}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 가격 변동 */}
          {hasPriceChange && (
            <div className={`inline-flex items-center gap-1 text-xs px-2 py-1 rounded-lg ${isAligned ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-white/5 text-gray-500 border border-white/10'}`}>
              {isAligned ? '✅' : '⏳'} 게시 당시 대비 {(r.price_change_pct ?? 0) >= 0 ? '+' : ''}{(r.price_change_pct ?? 0).toFixed(2)}%
              {r.target && <span className="text-gray-500 ml-1">({r.target})</span>}
            </div>
          )}

          {/* 하단: 출처 + 원문 */}
          <div className="flex items-center justify-between">
            <p className="text-[11px] text-gray-600">{r.source_desc || r.target}</p>
            {r.source_url && (
              <a href={r.source_url} target="_blank" rel="noopener noreferrer"
                className="text-[11px] text-gray-600 hover:text-gray-400 transition-colors">
                원문 →
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export function ReportAccordion({ reports, wsMap = {} }: { reports: ReportItem[]; wsMap?: Record<string, WallStreetData> }) {
  return (
    <div className="space-y-0">
      {reports.map(r => <AccordionItem key={r.id} r={r} wsMap={wsMap} />)}
    </div>
  );
}
