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
  related_stocks: string | null;
  action: string | null;
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

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return `${String(d.getMonth() + 1).padStart(2, '0')}/${String(d.getDate()).padStart(2, '0')}`;
}

function formatPrice(price: number, code: string | null): string {
  const isKr = /^\d{6}$/.test(code ?? '');
  if (isKr) return price.toLocaleString('ko-KR') + '원';
  return '$' + price.toFixed(2);
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
          <div className="flex flex-col items-end gap-0.5 shrink-0">
            <span className="text-xs font-bold">
              {resultStyle.icon} {resultStyle.label}
              {pred.result_val && <span className="ml-1 text-gray-400">({pred.result_val})</span>}
            </span>
            {pred.result_at && (
              <span className="text-[9px] text-gray-600">판정일: {formatDate(pred.result_at)}</span>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-end gap-0.5 shrink-0">
            <span className="text-[11px] text-gray-500">D-{remaining}</span>
            <span className="text-[9px] text-gray-600">만료 {formatDate(pred.expires_at)}</span>
          </div>
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

      {/* Action 추천 */}
      {pred.action && (() => {
        const label = pred.action.split(' · ')[0].trim();
        const reason = pred.action.includes(' · ') ? pred.action.slice(pred.action.indexOf(' · ') + 3) : null;
        let cls = 'bg-gray-500/20 text-gray-400 border-gray-500/20';
        if (label === '매수 고려' || label === '비중 확대') cls = 'bg-green-500/20 text-green-400 border-green-500/20';
        else if (label === '매도 고려' || label === '비중 축소') cls = 'bg-red-500/20 text-red-400 border-red-500/20';
        else if (label === '관망') cls = 'bg-yellow-500/20 text-yellow-400 border-yellow-500/20';
        const [bg, text, border] = cls.split(' ');
        return (
          <div className={`pl-7 mb-2`}>
            <div className={`inline-flex flex-col gap-0.5 px-3 py-2 rounded-xl ${bg} border ${border}`}>
              <span className={`text-sm font-bold ${text}`}>⚡ {label}</span>
              {reason && <span className={`text-[11px] ${text} opacity-70`}>{reason}</span>}
            </div>
          </div>
        );
      })()}

      {/* 관련 종목 */}
      {pred.related_stocks && (() => {
        try {
          const raw = JSON.parse(pred.related_stocks) as { name: string; code: string; reason: string }[];
          const stocks = raw.filter(s => s.name);
          if (!stocks.length) return null;
          return (
            <div className="pl-7 mb-3">
              <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wider mb-1.5">함께 볼 종목 (참고용)</p>
              <div className="flex flex-wrap gap-1.5 mb-1.5">
                {stocks.map((s, i) => {
                  const isKr = /^\d{6}$/.test(s.code);
                  const href = isKr
                    ? `https://finance.naver.com/item/main.naver?code=${s.code}`
                    : `https://finance.naver.com/world/sise.naver?symbol=${s.code}`;
                  return (
                    <a key={i} href={href} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/[0.06] hover:bg-white/[0.1] transition-colors group">
                      <span className="text-xs font-semibold text-gray-200 group-hover:text-white">{s.name}</span>
                      <span className="text-[10px] text-gray-600">{s.code}</span>
                    </a>
                  );
                })}
              </div>
              {stocks.some(s => s.reason) && (
                <div className="space-y-0.5">
                  {stocks.map((s, i) => s.reason ? (
                    <p key={i} className="text-[10px] text-gray-600">
                      <span className="text-gray-500">{s.name}</span> · {s.reason}
                    </p>
                  ) : null)}
                </div>
              )}
            </div>
          );
        } catch { return null; }
      })()}

      {/* 실시간 가격 추적 배지 */}
      {isPending && priceStatus.isTracking && priceStatus.badge && (
        <div className="pl-7 mb-3">
          <div className={`inline-flex flex-wrap items-center gap-x-1.5 gap-y-1 text-xs px-2.5 py-1.5 rounded-xl ${
            priceStatus.isAligned ? 'bg-green-500/15' : 'bg-white/[0.05]'
          }`}>
            <span>{priceStatus.isAligned ? '✅' : '⏳'}</span>
            {pred.entry_price != null && pred.current_price != null ? (
              <>
                <span className="text-gray-500">{formatPrice(pred.entry_price, pred.target_code)}</span>
                <span className="text-gray-600">→</span>
                <span className={`font-bold ${priceStatus.isAligned ? 'text-green-400' : 'text-gray-300'}`}>
                  {formatPrice(pred.current_price, pred.target_code)}
                </span>
                <span className={`font-bold ${priceStatus.isAligned ? 'text-green-400' : 'text-gray-400'}`}>
                  ({priceStatus.badge})
                </span>
              </>
            ) : (
              <span className={`font-bold ${priceStatus.isAligned ? 'text-green-400' : 'text-gray-400'}`}>
                게시 당시 대비 {priceStatus.badge}
              </span>
            )}
            <span className="text-[10px] text-gray-600">({pred.target})</span>
          </div>
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
