import { PredictionCard, type Prediction } from '@/components/PredictionCard';

async function getPredictions() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    const db = ctx?.env?.DB;
    if (!db) return { predictions: [], stats: { total: 0, hits: 0, hitRate: null } };

    const { results } = await db
      .prepare(`SELECT * FROM predictions ORDER BY created_at DESC LIMIT 50`)
      .all() as { results: Prediction[] };

    const statsRow = await db
      .prepare(
        `SELECT COUNT(*) as total,
                SUM(CASE WHEN result = 'hit' THEN 1 ELSE 0 END) as hits
         FROM predictions WHERE result IN ('hit','miss','partial')`
      )
      .first() as { total: number; hits: number } | null;

    const total = statsRow?.total ?? 0;
    const hits = statsRow?.hits ?? 0;
    return {
      predictions: results,
      stats: { total, hits, hitRate: total > 0 ? Math.round((hits / total) * 100) : null },
    };
  } catch {
    return { predictions: [], stats: { total: 0, hits: 0, hitRate: null } };
  }
}

export default async function PredictionsPage() {
  const { predictions, stats } = await getPredictions();

  const pending = predictions.filter((p) => p.result === null);
  const completed = predictions.filter((p) => p.result !== null);

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      {/* 헤더 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white mb-1">📊 예측 트래커</h1>
        <p className="text-sm text-gray-500">
          리포트·뉴스 분석을 바탕으로 AI가 생성한 예측과 실제 결과를 기록합니다.
        </p>
        <p className="text-[11px] text-gray-600 mt-1">
          ※ 투자 조언이 아닙니다. 참고 목적으로만 활용하세요.
        </p>
      </div>

      {/* 적중률 배지 */}
      {stats.total > 0 && (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] p-5 mb-8">
          <div className="flex items-center justify-between mb-3">
            <span className="text-sm font-semibold text-white">누적 적중률</span>
            <span className="text-2xl font-bold text-white">
              {stats.hitRate !== null ? `${stats.hitRate}%` : '-'}
            </span>
          </div>
          {/* 프로그레스 바 */}
          <div className="h-2 bg-white/[0.06] rounded-full overflow-hidden mb-2">
            <div
              className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full transition-all"
              style={{ width: `${stats.hitRate ?? 0}%` }}
            />
          </div>
          <p className="text-[11px] text-gray-500">
            총 {stats.total}건 결과 확정 · 적중 {stats.hits}건
          </p>
        </div>
      )}

      {/* 진행 중 예측 */}
      {pending.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">
            진행 중 ({pending.length})
          </h2>
          <div className="space-y-3">
            {pending.map((p) => (
              <PredictionCard key={p.id} pred={p} />
            ))}
          </div>
        </section>
      )}

      {/* 완료된 예측 */}
      {completed.length > 0 && (
        <section>
          <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3">
            결과 확정 ({completed.length})
          </h2>
          <div className="space-y-3">
            {completed.map((p) => (
              <PredictionCard key={p.id} pred={p} />
            ))}
          </div>
        </section>
      )}

      {/* 데이터 없음 */}
      {predictions.length === 0 && (
        <div className="text-center py-20 text-gray-600">
          <p className="text-4xl mb-4">🔮</p>
          <p className="text-sm">아직 생성된 예측이 없습니다.</p>
          <p className="text-xs mt-1">리포트 또는 트럼프 게시글이 감지되면 자동으로 생성됩니다.</p>
        </div>
      )}
    </div>
  );
}
