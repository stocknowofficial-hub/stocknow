import Link from 'next/link';
import { DashboardSidebar } from '@/components/DashboardSidebar';
import { MobileNav } from '@/components/MobileNav';
import { ShowMorePredictions, type PredictionRow, type WsConsensus } from '@/components/ShowMorePredictions';
import { getServerSession } from 'next-auth/next';
import { authOptions } from '@/lib/auth';
import { redirect } from 'next/navigation';

const INITIAL = 10;

// 진행중 우선순위: HIGH신뢰도 → 방향 일치 여부 → 만료 임박
const PENDING_ORDER = `
  CASE confidence WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END ASC,
  CASE
    WHEN direction = 'up' AND price_change_pct > 0 THEN 0
    WHEN direction = 'down' AND price_change_pct < 0 THEN 0
    ELSE 1
  END ASC,
  expires_at ASC
`;

const PRED_COLS = `id, source, source_desc, prediction, direction, target, target_code, result, result_at,
  entry_price, current_price, price_change_pct, price_updated_at, peak_change_pct, peak_at, hit_change_pct, hit_at,
  trade_setup, created_at, expires_at, confidence, basis`;

async function getHistoryData() {
  try {
    const { getCloudflareContext } = require('@opennextjs/cloudflare');
    const db = getCloudflareContext()?.env?.DB;
    if (!db) return null;

    const [statsRow, monthStatsRow, hitRows, hitCountRow, pendingRows, missRows] = await Promise.all([
      db.prepare(`
        SELECT
          COUNT(*) as total,
          SUM(CASE WHEN result = 'hit' THEN 1 ELSE 0 END) as hits,
          SUM(CASE WHEN result = 'miss' THEN 1 ELSE 0 END) as misses,
          SUM(CASE WHEN result IS NULL THEN 1 ELSE 0 END) as pending,
          ROUND(AVG(CASE WHEN result = 'hit' AND price_change_pct IS NOT NULL THEN price_change_pct END), 2) as avg_hit_pct,
          ROUND(AVG(CASE WHEN result = 'miss' AND price_change_pct IS NOT NULL THEN price_change_pct END), 2) as avg_miss_pct
        FROM predictions
      `).first(),
      db.prepare(`
        SELECT
          COUNT(*) as total,
          SUM(CASE WHEN result = 'hit' THEN 1 ELSE 0 END) as hits,
          SUM(CASE WHEN result = 'miss' THEN 1 ELSE 0 END) as misses,
          SUM(CASE WHEN result IS NULL THEN 1 ELSE 0 END) as pending,
          ROUND(AVG(CASE WHEN result = 'hit' AND price_change_pct IS NOT NULL THEN price_change_pct END), 2) as avg_hit_pct
        FROM predictions
        WHERE created_at >= date('now', 'start of month')
      `).first(),
      db.prepare(`SELECT ${PRED_COLS} FROM predictions WHERE result = 'hit' AND created_at >= date('now', 'start of month', '-1 month') ORDER BY ABS(COALESCE(peak_change_pct, hit_change_pct, price_change_pct, 0)) DESC LIMIT ${INITIAL}`).all(),
      db.prepare(`SELECT COUNT(*) as cnt FROM predictions WHERE result = 'hit' AND created_at >= date('now', 'start of month', '-1 month')`).first(),
      db.prepare(`SELECT ${PRED_COLS} FROM predictions WHERE result IS NULL ORDER BY ${PENDING_ORDER} LIMIT ${INITIAL}`).all(),
      db.prepare(`SELECT ${PRED_COLS} FROM predictions WHERE result = 'miss' ORDER BY created_at DESC LIMIT ${INITIAL}`).all(),
    ]);

    const s = statsRow as { total: number; hits: number; misses: number; pending: number; avg_hit_pct: number | null; avg_miss_pct: number | null } | null;
    const m = monthStatsRow as { total: number; hits: number; misses: number; pending: number; avg_hit_pct: number | null } | null;
    const recentHitCount = (hitCountRow as { cnt: number } | null)?.cnt ?? 0;

    // 초기 배치의 모든 종목 코드로 wallstreet_consensus 한번에 조회
    const allPreds = [
      ...(hitRows.results as PredictionRow[]),
      ...(pendingRows.results as PredictionRow[]),
      ...(missRows.results as PredictionRow[]),
    ];
    const tickers = [...new Set(
      allPreds.map(p => p.target_code)
              .filter((c): c is string => !!c && (/^[A-Za-z]{1,5}$/.test(c) || /^\d{6}$/.test(c)))
    )];

    let wsMap: Record<string, WsConsensus> = {};
    if (tickers.length > 0) {
      const ph = tickers.map(() => '?').join(',');
      const wsRows = await db.prepare(
        `SELECT ticker, recommendation, target_price, upside_pct, analyst_count FROM wallstreet_consensus WHERE ticker IN (${ph})`
      ).bind(...tickers).all() as { results: WsConsensus[] };
      wsMap = Object.fromEntries(wsRows.results.map(r => [r.ticker, r]));
    }

    return {
      stats: {
        total: s?.total ?? 0,
        hits: s?.hits ?? 0,
        misses: s?.misses ?? 0,
        pending: s?.pending ?? 0,
        hitRate: s && s.total > 0 ? Math.round((s.hits / s.total) * 100) : null,
        avgHitPct: s?.avg_hit_pct ?? null,
        avgMissPct: s?.avg_miss_pct ?? null,
      },
      monthStats: {
        total: m?.total ?? 0,
        hits: m?.hits ?? 0,
        misses: m?.misses ?? 0,
        pending: m?.pending ?? 0,
        // 적중률 = 적중 / 전체(진행중 포함)
        hitRate: m && m.total > 0 ? Math.round(((m?.hits ?? 0) / m.total) * 100) : null,
        avgHitPct: m?.avg_hit_pct ?? null,
      },
      recentHitCount,
      hits: hitRows.results as PredictionRow[],
      pending: pendingRows.results as PredictionRow[],
      misses: missRows.results as PredictionRow[],
      wsMap,
    };
  } catch {
    return null;
  }
}

export default async function HistoryPage() {
  const session = await getServerSession(authOptions);
  if (!session?.user) redirect('/auth/signin');

  const data = await getHistoryData();
  const provider = (session.user as { provider?: string }).provider;

  if (!data) {
    return (
      <div className="min-h-screen bg-[#0a0a0c] text-white flex items-center justify-center">
        <p className="text-gray-500">데이터를 불러올 수 없습니다.</p>
      </div>
    );
  }

  const { stats, monthStats, recentHitCount, hits, pending, misses, wsMap } = data;

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white">
      <div className="flex">
        <DashboardSidebar user={session.user} provider={provider} />
        <main className="flex-1">
          <div className="px-4 pt-6 pb-28 lg:px-12 lg:pt-10 lg:pb-12 max-w-3xl mx-auto">

            {/* 헤더 */}
            <header className="mb-8">
              <div className="flex items-center gap-2 mb-1">
                <Link href="/consensus" className="text-xs text-gray-600 hover:text-gray-400 transition-colors">컨센서스 ←</Link>
              </div>
              <h2 className="text-2xl lg:text-3xl font-bold mb-1">🎯 예측 성과 기록</h2>
              <p className="text-gray-500 text-sm">AI가 생성한 예측과 실제 결과를 추적합니다</p>
              <p className="text-[11px] text-gray-600 mt-1">※ 투자 조언이 아닙니다. 참고 목적으로만 활용하세요. 투자 판단과 손익 책임은 본인에게 있습니다.</p>
            </header>

            {/* 통계 카드 */}
            <div className="grid grid-cols-2 gap-3 mb-8">
              {/* 전체 누적 */}
              <div className="rounded-2xl bg-white/[0.03] border border-white/10 p-4">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-3">📊 전체 누적</p>
                <div className="flex items-end justify-between mb-3">
                  <div>
                    <p className="text-3xl font-black text-emerald-400">
                      {stats.hitRate != null ? `${stats.hitRate}%` : '-'}
                    </p>
                    <p className="text-[10px] text-gray-500 mt-0.5">적중률</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-black text-emerald-400">
                      {stats.avgHitPct != null ? `+${stats.avgHitPct.toFixed(1)}%` : '-'}
                    </p>
                    <p className="text-[10px] text-gray-500">적중 평균 수익</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-2 border-t border-white/5 flex-wrap">
                  <span className="text-[10px] text-emerald-500">✅ {stats.hits}건</span>
                  <span className="text-[10px] text-rose-400">❌ {stats.misses}건</span>
                  <span className="text-[10px] text-amber-400">⏳ {stats.pending}건</span>
                </div>
              </div>
              {/* 이번 달 */}
              <div className="rounded-2xl bg-emerald-500/10 border border-emerald-500/20 p-4">
                <p className="text-[10px] text-emerald-500 uppercase tracking-wider mb-3">🗓 이번 달({new Date().getMonth() + 1}월)</p>
                <div className="flex items-end justify-between mb-3">
                  <div>
                    <p className="text-3xl font-black text-emerald-400">
                      {monthStats.hitRate != null ? `${monthStats.hitRate}%` : monthStats.total === 0 ? '집계중' : '진행중'}
                    </p>
                    <p className="text-[10px] text-gray-500 mt-0.5">적중률</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xl font-black text-emerald-400">
                      {monthStats.avgHitPct != null ? `+${monthStats.avgHitPct.toFixed(1)}%` : '-'}
                    </p>
                    <p className="text-[10px] text-gray-500">적중 평균 수익</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 pt-2 border-t border-emerald-500/10 flex-wrap">
                  <span className="text-[10px] text-emerald-500">✅ {monthStats.hits}건</span>
                  <span className="text-[10px] text-rose-400">❌ {monthStats.misses}건</span>
                  <span className="text-[10px] text-amber-400">⏳ {monthStats.pending}건</span>
                  <span className="text-[10px] text-gray-500">총 {monthStats.total}건</span>
                </div>
              </div>
            </div>

            {/* 적중 예측 */}
            {recentHitCount > 0 && (
              <section className="mb-8">
                <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
                  ✅ 적중한 예측
                  <span className="text-sm font-normal text-emerald-400">{recentHitCount}건</span>
                </h3>
                <p className="text-[10px] text-gray-600 mb-3">최근 2개월 · 수익률 높은 순</p>
                <ShowMorePredictions initial={hits} total={recentHitCount} section="hit" wsMap={wsMap} />
              </section>
            )}

            {/* 진행중 예측 */}
            {stats.pending > 0 && (
              <section className="mb-8">
                <h3 className="text-base font-bold text-white mb-1 flex items-center gap-2">
                  ⏳ 진행중인 예측
                  <span className="text-sm font-normal text-amber-400">{stats.pending}건</span>
                </h3>
                <p className="text-[10px] text-gray-600 mb-3">HIGH 신뢰도 → 방향 일치 중 → 만료 임박 순</p>
                <ShowMorePredictions initial={pending} total={stats.pending} section="pending" wsMap={wsMap} />
              </section>
            )}

            {/* 빗나간 예측 */}
            {stats.misses > 0 && (
              <section className="mb-8">
                <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                  ❌ 빗나간 예측
                  <span className="text-sm font-normal text-rose-400">{stats.misses}건</span>
                </h3>
                <ShowMorePredictions initial={misses} total={stats.misses} section="miss" wsMap={wsMap} />
              </section>
            )}

            {stats.total === 0 && (
              <div className="text-center py-20 text-gray-600">
                <p className="text-4xl mb-4">🎯</p>
                <p className="text-sm">아직 결과가 확정된 예측이 없습니다.</p>
                <p className="text-xs mt-1">예측이 만료되면 자동으로 결과가 기록됩니다.</p>
              </div>
            )}

            <p className="text-[10px] text-gray-700 mt-4">※ 과거 성과는 미래 수익을 보장하지 않습니다. 투자 판단은 본인 책임입니다.</p>
          </div>
        </main>
      </div>
      <MobileNav />
    </div>
  );
}
