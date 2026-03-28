export const dynamic = 'force-dynamic';

import { TrumpFeed, type TrumpPrediction } from '@/components/TrumpFeed';

async function getTrumpData() {
  try {
    const { getCloudflareContext } = require("@opennextjs/cloudflare");
    const ctx = getCloudflareContext();
    const db = ctx?.env?.DB;
    if (!db) return null;

    const [{ results }, stats] = await Promise.all([
      db.prepare(`SELECT * FROM predictions WHERE source = 'trump' ORDER BY created_at DESC LIMIT 20`)
        .all() as Promise<{ results: TrumpPrediction[] }>,
      db.prepare(`SELECT COUNT(*) as total, SUM(CASE WHEN result = 'hit' THEN 1 ELSE 0 END) as hits FROM predictions WHERE source = 'trump' AND result IS NOT NULL`)
        .first() as Promise<{ total: number; hits: number } | null>,
    ]);

    return { predictions: results, stats };
  } catch {
    return null;
  }
}

export default async function TrumpPage() {
  const data = await getTrumpData();

  if (!data) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-8 text-center text-gray-600">
        <p className="text-4xl mb-4">🏛️</p>
        <p className="text-sm">데이터를 불러오지 못했습니다.</p>
      </div>
    );
  }

  const { predictions, stats } = data;
  const hitRate = stats && stats.total > 0 ? Math.round((stats.hits / stats.total) * 100) : null;

  return (
    <div className="min-h-screen bg-[#0a0a0c] text-white selection:bg-purple-500/30 font-sans pb-20">
      <div className="max-w-4xl mx-auto px-4 py-8 lg:px-12 lg:py-10">
        {/* 헤더 */}
        <div className="mb-8">
          <h1 className="text-2xl lg:text-3xl font-bold text-white mb-2">🏛️ 트럼프 마켓 임팩트</h1>
          <p className="text-sm text-gray-500">트럼프 Truth Social 게시글이 시장에 미치는 영향을 추적합니다.</p>
          <p className="text-[11px] text-gray-600 mt-1">※ 투자 조언이 아닙니다. 참고 목적으로만 활용하세요.</p>
        </div>

        {/* 적중률 */}
        {stats && stats.total > 0 && (
          <div className="rounded-2xl lg:rounded-3xl border border-orange-500/20 bg-gradient-to-br from-orange-500/10 to-amber-500/5 p-6 mb-8">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-xs font-bold uppercase tracking-wider mb-1 text-orange-400">트럼프 예측 적중률</p>
                <p className="text-xs text-gray-400">총 {stats.total}건 결과 확정 · 적중 {stats.hits}건</p>
              </div>
              <span className="text-4xl font-black text-white tracking-tight">{hitRate !== null ? `${hitRate}%` : '-'}</span>
            </div>
            <div className="h-2.5 bg-white/10 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-orange-500 to-amber-400 rounded-full"
                style={{ width: `${hitRate ?? 0}%` }} />
            </div>
          </div>
        )}

        {predictions.length === 0 ? (
          <div className="text-center py-20 text-gray-600">
            <p className="text-4xl mb-4">🏛️</p>
            <p className="text-sm">아직 수집된 트럼프 게시글이 없습니다.</p>
          </div>
        ) : (
          <TrumpFeed initialPosts={predictions} />
        )}
      </div>
    </div>
  );
}
