import Link from 'next/link';
import { MacroGauge, FG_ZONES, VIX_ZONES, getIntegratedComment } from '@/components/MacroGauge';
import { LastWeekPanel } from '@/components/LastWeekPanel';
import { ShowMoreReports } from '@/components/ShowMoreReports';
import { PredictionTableSection, type TableRow } from '@/components/PredictionTableSection';
import { ShowMoreTargets, type TargetDisplay, type SourceEntry } from '@/components/ShowMoreTargets';

const ETF_NAMES: Record<string, string> = {
  '069500': 'KODEX 200 (코스피)',
  '379800': 'KODEX S&P500',
  '133690': 'TIGER 나스닥100',
  '261220': 'KODEX WTI원유',
  '091160': 'KODEX 반도체',
  '228800': 'KODEX 금선물',
  '102110': 'TIGER 200',
  '308620': 'KODEX 차이나',
  '195930': 'TIGER 유럽',
  '195980': 'ARIRANG 신흥국',
  '114800': 'KODEX 인버스',
  '252670': 'KODEX 200선물인버스2X',
  '122630': 'KODEX 레버리지',
  '411060': 'ACE 미국나스닥100',
  '360750': 'TIGER 미국S&P500',
};

function getTargetName(target: string | null, code: string | null): string {
  if (code && ETF_NAMES[code]) return ETF_NAMES[code];
  if (target && ETF_NAMES[target]) return ETF_NAMES[target]; // target이 코드인 경우
  if (target && !/^\d+$/.test(target)) return target; // 숫자가 아닌 이름
  return target || code || '알 수 없음';
}

function getWeekLabel(): string {
  const now = new Date();
  const jan4 = new Date(now.getFullYear(), 0, 4);
  const startOfWeek1 = new Date(jan4);
  startOfWeek1.setDate(jan4.getDate() - ((jan4.getDay() + 6) % 7));
  const monday = new Date(now);
  monday.setDate(now.getDate() - ((now.getDay() + 6) % 7));
  const weekNo = Math.round((monday.getTime() - startOfWeek1.getTime()) / (7 * 86400000)) + 1;
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  const fmt = (d: Date) => `${d.getMonth() + 1}월 ${d.getDate()}일`;
  return `${now.getFullYear()}년 ${weekNo}주차 (${fmt(monday)} ~ ${fmt(sunday)})`;
}

type DirType = 'up' | 'down' | 'sideways';

interface TargetStat {
  target: string;
  target_code: string | null;
  up: number;
  down: number;
  sideways: number;
  count: number;
  dominant: DirType;
}

interface ReportRow {
  id: string;
  source: string;
  source_desc: string | null;
  source_url: string | null;
  prediction: string;
  direction: DirType;
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

interface AccuracyRow {
  id: string;
  source: string;
  prediction: string;
  direction: string;
  target: string;
  result: string;
  price_change_pct: number | null;
  created_at: string;
  expires_at: string;
}

interface WallStreetItem {
  ticker: string;
  name: string;
  recommendation: string;
  target_price: number | null;
  current_price: number | null;
  analyst_count: number;
  upside_pct: number | null;
  updated_at: string;
}

interface MacroRow {
  key: string;
  value: number;
  label: string;
  prev_close: number | null;
  week_ago: number | null;
  month_ago: number | null;
  updated_at: string | null;
}

async function getConsensusData() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    const db = ctx?.env?.DB;
    if (!db) return null;

    const [dirRes, targetRes, sourcesRes, reportRes, reportCountRes, accRes, accStats, lastWeekTargetRes, summaryRes, bestTradeRes, keyPointsRes, tableRes] = await Promise.all([
      db.prepare(`SELECT direction, COUNT(*) as cnt FROM predictions WHERE created_at >= datetime('now', '-7 days') AND source != 'trump' GROUP BY direction`).all(),
      db.prepare(`SELECT target, target_code, direction, COUNT(*) as cnt FROM predictions WHERE created_at >= datetime('now', '-7 days') AND source != 'trump' GROUP BY target, direction`).all(),
      db.prepare(`SELECT target, direction, source, date(created_at) as date FROM predictions WHERE created_at >= datetime('now', '-7 days') AND source != 'trump'`).all(),
      db.prepare(`SELECT id, source, source_desc, source_url, prediction, direction, target, target_code, confidence, created_at, key_points, related_stocks, action, trade_setup, price_change_pct, entry_price, current_price, expires_at FROM predictions WHERE created_at >= datetime('now', '-7 days') AND source != 'trump' ORDER BY created_at DESC LIMIT 10`).all(),
      db.prepare(`SELECT COUNT(*) as cnt FROM predictions WHERE created_at >= datetime('now', '-7 days') AND source != 'trump'`).first(),
      db.prepare(`SELECT id, source, prediction, direction, target, result, price_change_pct, peak_change_pct, peak_at, hit_change_pct, hit_at, created_at, expires_at FROM predictions WHERE result IS NOT NULL AND expires_at >= datetime('now', '-14 days') ORDER BY ABS(COALESCE(peak_change_pct, hit_change_pct, price_change_pct, 0)) DESC LIMIT 20`).all(),
      db.prepare(`SELECT COUNT(*) as total, SUM(CASE WHEN result = 'hit' THEN 1 ELSE 0 END) as hits, ROUND(AVG(CASE WHEN result = 'hit' AND hit_change_pct IS NOT NULL THEN hit_change_pct WHEN result = 'hit' AND price_change_pct IS NOT NULL THEN price_change_pct END), 2) as avg_hit_pct, ROUND(AVG(CASE WHEN result = 'miss' AND price_change_pct IS NOT NULL THEN price_change_pct END), 2) as avg_miss_pct FROM predictions WHERE result IS NOT NULL`).first(),
      db.prepare(`SELECT target, target_code, direction, COUNT(*) as cnt FROM predictions WHERE created_at >= datetime('now', '-14 days') AND created_at < datetime('now', '-7 days') AND source != 'trump' GROUP BY target, direction`).all(),
      db.prepare(`SELECT week_key, title, body, signal, updated_at FROM weekly_summary ORDER BY updated_at DESC LIMIT 1`).first().catch(() => null),
      db.prepare(`SELECT target, price_change_pct, direction FROM predictions WHERE result = 'hit' AND price_change_pct IS NOT NULL ORDER BY price_change_pct DESC LIMIT 1`).first().catch(() => null),
      db.prepare(`SELECT target, key_points FROM predictions WHERE created_at >= datetime('now', '-7 days') AND source != 'trump' AND key_points IS NOT NULL`).all(),
      db.prepare(`SELECT id, source, source_desc, source_url, target, target_code, direction, confidence, action, expires_at, created_at FROM predictions WHERE created_at >= datetime('now', '-7 days') AND source != 'trump' ORDER BY CASE confidence WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, created_at DESC LIMIT 300`).all(),
    ]);
    const accStatsTyped = accStats as { total: number; hits: number; avg_hit_pct: number | null; avg_miss_pct: number | null } | null;

    // 지난주 Top targets
    const lastWeekMap = new Map<string, TargetStat>();
    for (const row of lastWeekTargetRes.results as Array<{ target: string; target_code: string | null; direction: string; cnt: number }>) {
      const key = row.target;
      const existing = lastWeekMap.get(key) ?? { target: row.target, target_code: row.target_code, up: 0, down: 0, sideways: 0, count: 0, dominant: 'sideways' as DirType };
      if (row.direction === 'up') existing.up += row.cnt;
      else if (row.direction === 'down') existing.down += row.cnt;
      else existing.sideways += row.cnt;
      existing.count = existing.up + existing.down + existing.sideways;
      existing.dominant = existing.up >= existing.down && existing.up >= existing.sideways ? 'up' : existing.down >= existing.sideways ? 'down' : 'sideways';
      lastWeekMap.set(key, existing);
    }
    const lastWeekTargets = [...lastWeekMap.values()].sort((a, b) => b.count - a.count).slice(0, 8);

    // Direction counts
    const dirMap: Record<string, number> = { up: 0, down: 0, sideways: 0 };
    for (const row of dirRes.results as Array<{ direction: string; cnt: number }>) {
      const d = row.direction ?? 'sideways';
      dirMap[d] = (dirMap[d] ?? 0) + row.cnt;
    }
    const total = dirMap.up + dirMap.down + dirMap.sideways;

    // Target aggregation
    const targetMap = new Map<string, TargetStat>();
    for (const row of targetRes.results as Array<{ target: string; target_code: string | null; direction: string; cnt: number }>) {
      const key = row.target;
      const existing = targetMap.get(key) ?? { target: row.target, target_code: row.target_code, up: 0, down: 0, sideways: 0, count: 0, dominant: 'sideways' as DirType };
      if (row.direction === 'up') existing.up += row.cnt;
      else if (row.direction === 'down') existing.down += row.cnt;
      else existing.sideways += row.cnt;
      existing.count = existing.up + existing.down + existing.sideways;
      existing.dominant = existing.up >= existing.down && existing.up >= existing.sideways ? 'up' : existing.down >= existing.sideways ? 'down' : 'sideways';
      targetMap.set(key, existing);
    }
    const topTargets = [...targetMap.values()].sort((a, b) => b.count - a.count).slice(0, 30);

    // Macro 데이터 — 테이블 없어도 페이지 전체가 깨지지 않도록 분리
    const macroMap: Record<string, MacroRow> = {};
    try {
      const macroRes = await db.prepare(`SELECT * FROM macro_feed`).all();
      for (const row of macroRes.results as MacroRow[]) {
        macroMap[row.key] = row;
      }
    } catch {
      // macro_feed 테이블 미존재 시 빈 객체로 처리
    }

    // 월가 컨센서스 데이터
    let wallstreetItems: WallStreetItem[] = [];
    try {
      const wsRes = await db.prepare(`SELECT ticker, name, recommendation, target_price, current_price, analyst_count, upside_pct, updated_at FROM wallstreet_consensus ORDER BY updated_at DESC`).all();
      wallstreetItems = wsRes.results as WallStreetItem[];
    } catch { /* 테이블 없으면 빈 배열 */ }

    const weeklySummary = summaryRes as { week_key: string; title: string; body: string; signal: string; updated_at: string } | null;
    const bestTrade = bestTradeRes as { target: string; price_change_pct: number; direction: string } | null;

    // 종목별 key_points 집계 (상위 2개 키워드)
    const keyPointsMap = new Map<string, Map<string, number>>();
    for (const row of keyPointsRes.results as Array<{ target: string; key_points: string }>) {
      try {
        const points: string[] = JSON.parse(row.key_points);
        if (!keyPointsMap.has(row.target)) keyPointsMap.set(row.target, new Map());
        const kmap = keyPointsMap.get(row.target)!;
        for (const pt of points.slice(0, 3)) {
          kmap.set(pt, (kmap.get(pt) ?? 0) + 1);
        }
      } catch { /* ignore parse errors */ }
    }
    const topKeyPoints = new Map<string, string[]>();
    for (const [target, kmap] of keyPointsMap) {
      const sorted = [...kmap.entries()].sort((a, b) => b[1] - a[1]).slice(0, 2).map(e => e[0]);
      topKeyPoints.set(target, sorted);
    }

    const reportTotal = (reportCountRes as { cnt: number } | null)?.cnt ?? 0;

    return {
      weekLabel: getWeekLabel(),
      reportCount: total,
      reportTotal,

      tableRows: tableRes.results,
      direction: { up: dirMap.up, down: dirMap.down, sideways: dirMap.sideways, total },
      topTargets,
      lastWeekTargets,
      reports: reportRes.results as ReportRow[],
      accuracy: accRes.results as AccuracyRow[],
      macro: macroMap,
      weeklySummary,
      bestTrade,
      topKeyPoints: Object.fromEntries(topKeyPoints),
      sources: sourcesRes.results as Array<{ target: string; direction: string; source: string; date: string }>,
      wallstreet: wallstreetItems,
      accuracyStats: {
        total: accStatsTyped?.total ?? 0,
        hits: accStatsTyped?.hits ?? 0,
        hitRate: accStatsTyped && accStatsTyped.total > 0 ? Math.round((accStatsTyped.hits / accStatsTyped.total) * 100) : null,
        avgHitPct: accStatsTyped?.avg_hit_pct ?? null,
        avgMissPct: accStatsTyped?.avg_miss_pct ?? null,
      },
    };
  } catch {
    return null;
  }
}

function DirIcon({ dir }: { dir: string }) {
  if (dir === 'up') return <span className="font-bold text-emerald-400">↑</span>;
  if (dir === 'down') return <span className="font-bold text-rose-400">↓</span>;
  return <span className="text-gray-400">→</span>;
}


function ResultBadge({ result }: { result: string }) {
  if (result === 'hit') return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">✅ 적중</span>;
  if (result === 'miss') return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-rose-500/10 text-rose-400 border border-rose-500/20">❌ 빗나감</span>;
  return <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/5 text-gray-400 border border-white/10">보류</span>;
}

export default async function ConsensusPage() {
  const data = await getConsensusData();

  if (!data) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8 text-center text-gray-600 py-20">
        <p className="text-4xl mb-4">🧭</p>
        <p className="text-sm">데이터를 불러오지 못했습니다.</p>
      </div>
    );
  }

  const { direction, topTargets, lastWeekTargets, reports, accuracy, accuracyStats, weekLabel, reportCount, reportTotal, tableRows, macro, weeklySummary, bestTrade, topKeyPoints, wallstreet, sources } = data;

  const fg = macro?.fear_greed ?? null;
  const vix = macro?.vix ?? null;

  const topBullish = topTargets
    .filter(t => t.dominant === 'up')
    .map(t => ({ name: getTargetName(t.target, t.target_code), count: t.up }));
  const topBearish = topTargets
    .filter(t => t.dominant === 'down')
    .map(t => ({ name: getTargetName(t.target, t.target_code), count: t.down }));

  const macroComment = getIntegratedComment(fg?.value ?? null, vix?.value ?? null, topBullish, topBearish);

  // 종목별 언급 출처 맵 구성 (source + date)
  const sourcesMap = new Map<string, { up: SourceEntry[]; down: SourceEntry[] }>();
  for (const row of sources) {
    const entry = sourcesMap.get(row.target) ?? { up: [], down: [] };
    if (row.direction === 'up') entry.up.push({ source: row.source, date: row.date });
    else if (row.direction === 'down') entry.down.push({ source: row.source, date: row.date });
    sourcesMap.set(row.target, entry);
  }

  // ShowMoreTargets용 데이터 변환
  const bullishTargets: TargetDisplay[] = topTargets
    .filter(t => t.dominant === 'up')
    .map(t => ({
      displayName: getTargetName(t.target, t.target_code),
      target_code: t.target_code,
      up: t.up, down: t.down, count: t.count, dominant: t.dominant,
      keyPoints: topKeyPoints[t.target] ?? [],
      upSources: sourcesMap.get(t.target)?.up ?? [],
      downSources: sourcesMap.get(t.target)?.down ?? [],
    }));
  const bearishTargets: TargetDisplay[] = topTargets
    .filter(t => t.dominant === 'down')
    .map(t => ({
      displayName: getTargetName(t.target, t.target_code),
      target_code: t.target_code,
      up: t.up, down: t.down, count: t.count, dominant: t.dominant,
      keyPoints: topKeyPoints[t.target] ?? [],
      upSources: sourcesMap.get(t.target)?.up ?? [],
      downSources: sourcesMap.get(t.target)?.down ?? [],
    }));
  const sidewaysTargets: TargetDisplay[] = topTargets
    .filter(t => t.dominant === 'sideways')
    .map(t => ({
      displayName: getTargetName(t.target, t.target_code),
      target_code: t.target_code,
      up: t.up, down: t.down, count: t.count, dominant: t.dominant,
      keyPoints: [],
      upSources: sourcesMap.get(t.target)?.up ?? [],
      downSources: sourcesMap.get(t.target)?.down ?? [],
    }));

  // reportRes는 이미 source != 'trump' 필터 적용된 상태
  const reportItems = reports;
  const trumpItems: ReportRow[] = []; // trump는 별도 페이지에서 관리

  // 주요 방향 결론
  const dominant = direction.up >= direction.down && direction.up >= direction.sideways ? 'up'
    : direction.down >= direction.sideways ? 'down' : 'sideways';
  const dominantLabel = dominant === 'up' ? '📈 전반적 상승 우세' : dominant === 'down' ? '📉 전반적 하락 우세' : '→ 방향 혼재';
  const dominantColor = dominant === 'up' ? 'text-green-400' : dominant === 'down' ? 'text-red-400' : 'text-gray-400';

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white selection:bg-purple-500/30 font-sans pb-20">
      <div className="max-w-4xl mx-auto px-4 py-8 lg:px-12 lg:py-10">
        {/* 헤더 */}
        <div className="mb-8">
          <h1 className="text-2xl lg:text-3xl font-bold text-white mb-2">🧭 주간 컨센서스</h1>
          <p className="text-sm text-gray-500">{weekLabel} · 증권사 리포트 {reportTotal}건</p>
          <p className="text-[11px] text-gray-600 mt-1">※ 투자 조언이 아닙니다. 참고 목적으로만 활용하세요. 투자 판단과 손익 책임은 본인에게 있습니다.</p>
        </div>

        {/* AI 주간 핵심 뷰 카드 */}
        {weeklySummary && (() => {
          const signalStyle =
            weeklySummary.signal === 'bullish' ? { border: 'border-emerald-500/30', bg: 'from-emerald-500/10 to-emerald-900/5', badge: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30', icon: '📈', label: '강세' } :
              weeklySummary.signal === 'bearish' ? { border: 'border-rose-500/30', bg: 'from-rose-500/10 to-rose-900/5', badge: 'bg-rose-500/20 text-rose-400 border-rose-500/30', icon: '📉', label: '약세' } :
                weeklySummary.signal === 'caution' ? { border: 'border-amber-500/30', bg: 'from-amber-500/10 to-amber-900/5', badge: 'bg-amber-500/20 text-amber-400 border-amber-500/30', icon: '⚠️', label: '주의' } :
                  { border: 'border-white/10', bg: 'from-white/5 to-transparent', badge: 'bg-white/10 text-gray-400 border-white/10', icon: '→', label: '중립' };

          // body가 JSON이면 구조화, 아니면 레거시 텍스트로 처리
          let structured: { situation?: string; analysis?: string; action?: string } | null = null;
          try { structured = JSON.parse(weeklySummary.body); } catch { /* legacy plain text */ }

          return (
            <div className={`rounded-2xl lg:rounded-3xl border ${signalStyle.border} bg-gradient-to-br ${signalStyle.bg} p-6 lg:p-8 mb-6`}>
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500">🤖 AI 통합 분석</span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${signalStyle.badge}`}>
                  {signalStyle.icon} {signalStyle.label}
                </span>
                <span className="text-[10px] text-gray-600 ml-auto">
                  {new Date(weeklySummary.updated_at + 'Z').toLocaleString('ko-KR', {
                    month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit', hour12: false,
                    timeZone: 'Asia/Seoul',
                  })} 업데이트
                </span>
              </div>
              <p className="text-base lg:text-lg font-bold text-white mb-4 leading-snug">{weeklySummary.title}</p>

              {structured?.situation ? (
                <div className="space-y-3">
                  {structured.situation && (
                    <div className="rounded-xl bg-black/20 border border-white/[0.06] px-4 py-3">
                      <p className="text-xs text-rose-400 font-bold mb-1">🚨 현재 상황</p>
                      <p className="text-sm text-gray-200 leading-relaxed">{structured.situation.replace(/^🚨\s*현재 상황:\s*/i, '')}</p>
                    </div>
                  )}
                  {structured.analysis && (
                    <div className="rounded-xl bg-black/20 border border-white/[0.06] px-4 py-3">
                      <p className="text-xs text-blue-400 font-bold mb-1">📊 월가 시그널</p>
                      <p className="text-sm text-gray-200 leading-relaxed">{structured.analysis.replace(/^📊\s*월가 시그널:\s*/i, '')}</p>
                    </div>
                  )}
                  {structured.action && (
                    <div className="rounded-xl bg-black/20 border border-white/[0.06] px-4 py-3">
                      <p className="text-xs text-amber-400 font-bold mb-1">💡 Action Point</p>
                      <p className="text-sm text-gray-200 leading-relaxed">{structured.action.replace(/^💡\s*Action Point:\s*/i, '')}</p>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-sm text-gray-300 leading-relaxed whitespace-pre-line">{weeklySummary.body}</p>
              )}
              <p className="text-[10px] text-gray-600 mt-3">※ AI 자동 분석 · 투자 조언 아님 · 매크로 + 증권사 리포트 + 트럼프 SNS 종합</p>
            </div>
          );
        })()}



        {/* 매크로 시그널 — 게이지 2개 + 코멘트 */}
        <div className="rounded-2xl lg:rounded-3xl border border-white/10 bg-white/[0.03] p-6 lg:p-8 mb-6">
          <div className="mb-4">
            <h3 className="text-base font-bold text-white">📡 매크로 시그널</h3>
            <p className="text-[10px] text-gray-500 mt-0.5">
              CNN Fear &amp; Greed · CBOE VIX · 30분 갱신
              {fg?.updated_at && (
                <span className="ml-1">
                  · 최종 업데이트:{' '}
                  {new Date(fg.updated_at + 'Z').toLocaleString('ko-KR', {
                    month: '2-digit', day: '2-digit',
                    hour: '2-digit', minute: '2-digit', hour12: false,
                    timeZone: 'Asia/Seoul',
                  })}
                </span>
              )}
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4 mb-4">
            <MacroGauge
              title="CNN Fear & Greed"
              value={fg?.value ?? null}
              label={fg?.label ?? null}
              maxValue={100}
              zones={FG_ZONES}
              prevClose={fg?.prev_close}
              weekAgo={fg?.week_ago}
              monthAgo={fg?.month_ago}
            />
            <MacroGauge
              title="CBOE VIX"
              value={vix?.value ?? null}
              label={vix?.label ?? null}
              maxValue={60}
              zones={VIX_ZONES}
              prevClose={vix?.prev_close}
              weekAgo={vix?.week_ago}
            />
          </div>
          {/* rule-based 코멘트 */}
          <div className="rounded-xl bg-white/[0.03] border border-white/[0.06] px-4 py-3">
            <p className="text-[10px] text-gray-600 mb-1 font-semibold uppercase tracking-wider">AI 시그널 코멘트</p>
            <p className={`text-sm font-medium ${macroComment.color}`}>{macroComment.text}</p>
            <p className="text-[10px] text-gray-600 mt-1">※ 참고 목적 자동 분석입니다. 투자 조언이 아닙니다.</p>
          </div>
        </div>

        {/* 예측 성과 링크 배너 */}
        <Link href="/history" className="flex items-center justify-between rounded-2xl lg:rounded-3xl border border-emerald-500/20 bg-emerald-500/5 hover:bg-emerald-500/10 transition-colors p-4 mb-8 group">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🎯</span>
            <div>
              <p className="text-sm font-bold text-white">AI 예측 성과 기록</p>
              <p className="text-xs text-gray-400">
                {accuracyStats.total > 0
                  ? `총 ${accuracyStats.total}건 확정 · 적중률 ${accuracyStats.hitRate}% · 적중 평균 ${accuracyStats.avgHitPct != null ? `+${accuracyStats.avgHitPct.toFixed(1)}%` : '-'}`
                  : '예측 결과 집계 중'}
              </p>
            </div>
          </div>
          <span className="text-gray-500 group-hover:text-gray-300 transition-colors text-sm">전체 보기 →</span>
        </Link>

        {reportCount === 0 ? (
          <div className="text-center py-20 text-gray-600">
            <p className="text-4xl mb-4">🧭</p>
            <p className="text-sm">이번 주 분석된 리포트가 없습니다.</p>
            <p className="text-xs mt-1">매주 월~금 오전에 주요 증권사 리포트가 자동 수집됩니다.</p>
          </div>
        ) : (
          <>
            {/* 컨센서스 통합 카드 */}
            <div className="rounded-2xl lg:rounded-3xl border border-white/10 bg-white/[0.03] p-6 lg:p-8 mb-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-base font-bold text-white">📊 이번 주 컨센서스</h3>
                  <p className="text-[10px] text-gray-500 mt-0.5">증권사 리포트 {direction.total}건 기준</p>
                </div>
              </div>
              <p className={`text-lg font-bold mb-5 ${dominantColor}`}>{dominantLabel}</p>

              <ShowMoreTargets
                bullish={bullishTargets}
                bearish={bearishTargets}
                sideways={sidewaysTargets}
                total={direction.total}
              />

              {/* 지난 주 비교 (토글) */}
              {(() => {
                const thisWeekMap = new Map(topTargets.map(t => [t.target, t]));
                const lastBullish = lastWeekTargets
                  .filter(t => t.dominant === 'up')
                  .map(t => ({
                    name: getTargetName(t.target, t.target_code),
                    count: t.up,
                    thisCount: (() => { const w = thisWeekMap.get(t.target); return w?.dominant === 'up' ? w.up : 0; })(),
                  }));
                const lastBearish = lastWeekTargets
                  .filter(t => t.dominant === 'down')
                  .map(t => ({
                    name: getTargetName(t.target, t.target_code),
                    count: t.down,
                    thisCount: (() => { const w = thisWeekMap.get(t.target); return w?.dominant === 'down' ? w.down : 0; })(),
                  }));
                return <LastWeekPanel lastBullish={lastBullish} lastBearish={lastBearish} />;
              })()}
            </div>

            {/* 분석 결과 요약 테이블 */}
            {tableRows && tableRows.length > 0 && (
              <div className="rounded-2xl lg:rounded-3xl border border-white/10 bg-white/[0.03] p-6 lg:p-8 mb-6">
                <div className="mb-4">
                  <h3 className="text-base font-bold text-white">📋 이번 주 TOP 10 시그널</h3>
                  <p className="text-[10px] text-gray-500 mt-0.5">전체 {reportTotal}건 · 신뢰도 → 최신순 · 상세 내용은 아래 리포트에서</p>
                </div>
                <PredictionTableSection rows={tableRows as TableRow[]} />
              </div>
            )}

            {/* 증권사 리포트 상세 (accordion) */}
            {reportItems.length > 0 && (
              <div id="reports-section" className="rounded-2xl lg:rounded-3xl border border-white/10 bg-white/[0.03] p-6 lg:p-8 mb-6">
                <div className="mb-4">
                  <h3 className="text-base font-bold text-white">📑 AI 분석 결과 ({reportTotal}건)</h3>
                  <p className="text-[10px] text-gray-500 mt-0.5">증권사 리포트 분석 · 최신 10건 표시</p>
                </div>
                <ShowMoreReports
                  reports={reportItems}
                  total={reportTotal}
                  wsMap={Object.fromEntries((wallstreet ?? []).map(w => [w.ticker, w]))}
                />
              </div>
            )}

            {/* 트럼프 링크 */}
            {trumpItems.length > 0 && (
              <div className="rounded-2xl lg:rounded-3xl border border-orange-500/20 bg-orange-500/5 p-6 lg:p-8 mb-6 flex items-center justify-between">
                <div>
                  <p className="text-sm font-semibold text-orange-400">🏛️ 트럼프 SNS 예측 {trumpItems.length}건</p>
                  <p className="text-[11px] text-gray-500 mt-0.5">트럼프 게시글의 시장 영향 분석</p>
                </div>
                <a href="/trump" className="text-xs text-orange-400 hover:text-orange-300 font-semibold">
                  보러가기 →
                </a>
              </div>
            )}

          </>
        )}
      </div>
    </div>
  );
}
