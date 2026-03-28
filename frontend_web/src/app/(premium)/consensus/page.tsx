import { ReportAccordion } from '@/components/ReportAccordion';

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
  created_at: string;
  expires_at: string;
}

async function getConsensusData() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    const db = ctx?.env?.DB;
    if (!db) return null;

    const [dirRes, targetRes, reportRes, accRes, accStats] = await Promise.all([
      db.prepare(`SELECT direction, COUNT(*) as cnt FROM predictions WHERE created_at >= datetime('now', '-7 days') AND source != 'trump' GROUP BY direction`).all(),
      db.prepare(`SELECT target, target_code, direction, COUNT(*) as cnt FROM predictions WHERE created_at >= datetime('now', '-7 days') AND source != 'trump' GROUP BY target, direction`).all(),
      db.prepare(`SELECT id, source, source_desc, source_url, prediction, direction, target, target_code, confidence, created_at, key_points, related_stocks, action, trade_setup, price_change_pct, expires_at FROM predictions WHERE created_at >= datetime('now', '-7 days') ORDER BY created_at DESC`).all(),
      db.prepare(`SELECT id, source, prediction, direction, target, result, created_at, expires_at FROM predictions WHERE result IS NOT NULL AND expires_at >= datetime('now', '-14 days') ORDER BY expires_at DESC LIMIT 20`).all(),
      db.prepare(`SELECT COUNT(*) as total, SUM(CASE WHEN result = 'hit' THEN 1 ELSE 0 END) as hits FROM predictions WHERE result IS NOT NULL`).first(),
    ]);
    const accStatsTyped = accStats as { total: number; hits: number } | null;

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
    const topTargets = [...targetMap.values()].sort((a, b) => b.count - a.count).slice(0, 8);

    return {
      weekLabel: getWeekLabel(),
      reportCount: total,
      direction: { up: dirMap.up, down: dirMap.down, sideways: dirMap.sideways, total },
      topTargets,
      reports: reportRes.results as ReportRow[],
      accuracy: accRes.results as AccuracyRow[],
      accuracyStats: {
        total: accStatsTyped?.total ?? 0,
        hits: accStatsTyped?.hits ?? 0,
        hitRate: accStatsTyped && accStatsTyped.total > 0 ? Math.round((accStatsTyped.hits / accStatsTyped.total) * 100) : null,
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

  const { direction, topTargets, reports, accuracy, accuracyStats, weekLabel, reportCount } = data;

  // 리포트 vs 트럼프 SNS 분리
  const reportItems = reports.filter(r => r.source.toLowerCase() !== 'trump');
  const trumpItems = reports.filter(r => r.source.toLowerCase() === 'trump');

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
          <p className="text-sm text-gray-500">{weekLabel} · 증권사 리포트 {reportItems.length}건 · 트럼프 SNS {trumpItems.length}건</p>
          <p className="text-[11px] text-gray-600 mt-1">※ 투자 조언이 아닙니다. 참고 목적으로만 활용하세요.</p>
        </div>

        {/* 적중률 배너 — 상단 항상 표시 */}
        <div className={`rounded-2xl lg:rounded-3xl border p-6 mb-8 flex items-center justify-between ${accuracyStats.total > 0 ? 'border-green-500/20 bg-gradient-to-br from-green-500/10 to-emerald-500/5' : 'border-white/[0.06] bg-white/[0.03]'}`}>
          <div>
            <p className={`text-xs font-bold uppercase tracking-wider mb-1 ${accuracyStats.total > 0 ? 'text-green-400' : 'text-gray-500'}`}>AI 누적 예측 적중률</p>
            <p className="text-xs text-gray-400">
              {accuracyStats.total > 0
                ? `총 ${accuracyStats.total}건 결과 확정 · 적중 ${accuracyStats.hits}건`
                : '예측 결과 집계 중 · 곧 공개됩니다'}
            </p>
          </div>
          <div className="text-right">
            {accuracyStats.total > 0
              ? <span className="text-4xl font-black text-green-400 tracking-tight">{accuracyStats.hitRate}%</span>
              : <span className="text-xl font-bold text-gray-500">추적 중</span>
            }
          </div>
        </div>

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

            {/* 강세 자산 */}
            {topTargets.filter(t => t.dominant === 'up').length > 0 && (
              <div className="mb-4">
                <p className="text-[11px] font-bold text-green-400 mb-2">📈 강세 전망</p>
                <div className="space-y-2">
                  {topTargets.filter(t => t.dominant === 'up').map(t => (
                    <div key={t.target}>
                      <div className="flex justify-between text-xs mb-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-gray-200">{getTargetName(t.target, t.target_code)}</span>
                          {t.target_code && t.target_code.length <= 6 && (
                            <span className="text-[10px] text-gray-600">{t.target_code}</span>
                          )}
                        </div>
                        <span className="text-green-400">{t.up}곳 언급</span>
                      </div>
                      <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full"
                          style={{ width: `${Math.round((t.up / direction.total) * 100)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 약세 자산 */}
            {topTargets.filter(t => t.dominant === 'down').length > 0 && (
              <div className="mb-4">
                <p className="text-[11px] font-bold text-red-400 mb-2">📉 약세 전망</p>
                <div className="space-y-2">
                  {topTargets.filter(t => t.dominant === 'down').map(t => (
                    <div key={t.target}>
                      <div className="flex justify-between text-xs mb-1">
                        <div className="flex items-center gap-1.5">
                          <span className="text-gray-200">{getTargetName(t.target, t.target_code)}</span>
                          {t.target_code && t.target_code.length <= 6 && (
                            <span className="text-[10px] text-gray-600">{t.target_code}</span>
                          )}
                        </div>
                        <span className="text-red-400">{t.down}곳 언급</span>
                      </div>
                      <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-red-500 to-rose-400 rounded-full"
                          style={{ width: `${Math.round((t.down / direction.total) * 100)}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* 혼재 자산 */}
            {topTargets.filter(t => t.dominant === 'sideways').length > 0 && (
              <div>
                <p className="text-[11px] font-bold text-gray-500 mb-2">→ 방향 혼재</p>
                <div className="flex flex-wrap gap-2">
                  {topTargets.filter(t => t.dominant === 'sideways').map(t => (
                    <span key={t.target} className="text-[11px] text-gray-500 bg-white/5 px-2 py-1 rounded-lg">
                      {getTargetName(t.target, t.target_code)} ({t.count}건)
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 증권사 리포트 요약 (accordion) */}
          {reportItems.length > 0 && (
            <div className="rounded-2xl lg:rounded-3xl border border-white/10 bg-white/[0.03] p-6 lg:p-8 mb-6">
              <div className="mb-4">
                <h3 className="text-base font-bold text-white">📑 증권사 리포트 ({reportItems.length}건)</h3>
                <p className="text-[10px] text-gray-500 mt-0.5">주요 증권사 시황 및 종목 분석</p>
              </div>              <ReportAccordion reports={reportItems} />
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

          {/* 최근 예측 결과 */}
          {accuracy.length > 0 && (
            <div className="rounded-2xl lg:rounded-3xl border border-white/10 bg-white/[0.03] p-6 lg:p-8 mb-6">
              <div className="mb-4">
                <h3 className="text-base font-bold text-white">🎯 최근 예측 결과</h3>
                <p className="text-[10px] text-gray-500 mt-0.5">최근 2주 내 만료된 예측의 적중 여부</p>
              </div>
              <div className="space-y-2">
                {accuracy.map((a) => (
                  <div key={a.id} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2 min-w-0">
                      <DirIcon dir={a.direction} />
                      <span className="text-gray-400 truncate">{a.source} · {a.prediction}</span>
                    </div>
                    <ResultBadge result={a.result} />
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
      </div>
    </div>
  );
}
