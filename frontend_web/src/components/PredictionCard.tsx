'use client';

export interface Prediction {
  id: string;
  created_at: string;
  source: string;
  source_desc: string | null;
  source_url: string | null;
  prediction: string;
  direction: 'up' | 'down' | 'sideways';
  target: string;
  target_code: string | null;
  basis: string | null;
  key_points: string | null;
  timeframe: number;
  expires_at: string;
  confidence: 'high' | 'medium' | 'low';
  result: string | null;
  result_val: string | null;
  result_at: string | null;
  entry_price: number | null;
  current_price: number | null;
  price_change_pct: number | null;
  price_updated_at: string | null;
}

const SOURCE_LABEL: Record<string, string> = {
  blackrock: 'BlackRock',
  kiwoom: '키움증권',
  trump: '트럼프 Truth Social',
  briefing: '시황 브리핑',
};

const DIRECTION_ICON: Record<string, string> = {
  up: '📈',
  down: '📉',
  sideways: '➡️',
};

const CONFIDENCE_LABEL: Record<string, { label: string; color: string }> = {
  high:   { label: 'HIGH',   color: 'text-red-400' },
  medium: { label: 'MEDIUM', color: 'text-yellow-400' },
  low:    { label: 'LOW',    color: 'text-gray-500' },
};

const RESULT_STYLE: Record<string, { icon: string; label: string; border: string; bg: string }> = {
  hit:            { icon: '✅', label: '적중',    border: 'border-green-500/30',  bg: 'bg-green-500/5' },
  miss:           { icon: '❌', label: '미적중',  border: 'border-red-500/30',    bg: 'bg-red-500/5' },
  partial:        { icon: '🔶', label: '부분 적중', border: 'border-yellow-500/30', bg: 'bg-yellow-500/5' },
  pending_review: { icon: '🔍', label: '검토 중',  border: 'border-gray-500/30',   bg: 'bg-white/[0.02]' },
};

function daysLeft(expiresAt: string): number {
  const diff = new Date(expiresAt).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

function getPriceStatus(pred: Prediction): { isTracking: boolean; isAligned: boolean; badge: string | null } {
  if (pred.price_change_pct === null || pred.price_change_pct === undefined) {
    return { isTracking: false, isAligned: false, badge: null };
  }
  const pct = pred.price_change_pct;
  const aligned =
    (pred.direction === 'up' && pct > 0) ||
    (pred.direction === 'down' && pct < 0);
  const sign = pct >= 0 ? '+' : '';
  return {
    isTracking: true,
    isAligned: aligned,
    badge: `${sign}${pct.toFixed(2)}%`,
  };
}

export function PredictionCard({ pred }: { pred: Prediction }) {
  const isPending = pred.result === null;
  const resultStyle = pred.result ? RESULT_STYLE[pred.result] ?? RESULT_STYLE['pending_review'] : null;
  const conf = CONFIDENCE_LABEL[pred.confidence] ?? CONFIDENCE_LABEL['medium'];
  const remaining = isPending ? daysLeft(pred.expires_at) : 0;
  const priceStatus = getPriceStatus(pred);

  // 예측 방향 일치 시 카드 테두리 강조
  const borderClass = resultStyle
    ? `${resultStyle.border} ${resultStyle.bg}`
    : priceStatus.isAligned
      ? 'border-green-500/25 bg-green-500/[0.04]'
      : 'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]';

  return (
    <div className={`rounded-2xl border p-4 transition-colors ${borderClass}`}>
      {/* 헤더 */}
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          {/* 출처 뱃지 */}
          <span className="text-[10px] bg-white/[0.06] text-gray-400 rounded-md px-2 py-0.5">
            {SOURCE_LABEL[pred.source] ?? pred.source}
          </span>
          {/* 신뢰도 */}
          <span className={`text-[10px] font-bold ${conf.color}`}>
            ● {conf.label}
          </span>
        </div>
        {/* 결과 or 남은 일수 */}
        {resultStyle ? (
          <span className="text-xs font-bold shrink-0">
            {resultStyle.icon} {resultStyle.label}
            {pred.result_val && <span className="ml-1 text-gray-400">({pred.result_val})</span>}
          </span>
        ) : (
          <span className="text-[11px] text-gray-500 shrink-0">
            D-{remaining}
          </span>
        )}
      </div>

      {/* 예측 본문 */}
      <div className="flex items-start gap-2 mb-2">
        <span className="text-lg shrink-0">{DIRECTION_ICON[pred.direction] ?? '🔮'}</span>
        <p className="text-sm font-semibold text-white leading-snug">{pred.prediction}</p>
      </div>

      {/* 핵심 근거 (key_points 우선, 없으면 basis) */}
      {pred.key_points ? (
        <ul className="pl-7 mb-2 space-y-1">
          {(JSON.parse(pred.key_points) as string[]).map((point, i) => (
            <li key={i} className="text-[11px] text-gray-400 leading-relaxed flex gap-1.5">
              <span className="text-gray-600 shrink-0">•</span>
              <span>{point}</span>
            </li>
          ))}
        </ul>
      ) : pred.basis ? (
        <p className="text-[11px] text-gray-500 mb-2 pl-7 leading-relaxed">{pred.basis}</p>
      ) : null}

      {/* 실시간 가격 추적 배지 */}
      {isPending && priceStatus.isTracking && priceStatus.badge && (
        <div className="pl-7 mb-3">
          <span className={`inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-1 rounded-full ${
            priceStatus.isAligned
              ? 'bg-green-500/15 text-green-400'
              : 'bg-white/[0.05] text-gray-400'
          }`}>
            {priceStatus.isAligned ? '✅' : '⏳'} 리포트 당시 대비 {priceStatus.badge}
            <span className="font-normal text-[10px] opacity-60">
              ({pred.target})
            </span>
          </span>
        </div>
      )}

      {/* 하단 메타 */}
      <div className="flex items-center justify-between gap-2 pl-7">
        <span className="text-[10px] text-gray-600">
          {pred.source_desc ?? ''}
        </span>
        <div className="flex items-center gap-2">
          {pred.target_code && (
            <span className="text-[10px] text-gray-600">{pred.target_code}</span>
          )}
          <span className="text-[10px] text-gray-600">
            {new Date(pred.created_at).toLocaleDateString('ko-KR', { month: 'numeric', day: 'numeric' })} 예측
          </span>
          {pred.source_url && (
            <a
              href={pred.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-[10px] text-blue-500 hover:underline"
            >
              원문 →
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
