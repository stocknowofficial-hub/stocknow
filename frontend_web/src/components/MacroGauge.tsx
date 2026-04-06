// SVG 반원 게이지 컴포넌트 (server component — no 'use client' needed)

const CX = 100;
const CY = 100;
const R_OUT = 88;
const R_IN = 62;

/** 정규화된 위치 t (0=왼쪽, 1=오른쪽)에서 반원 위의 좌표 반환 */
function pt(t: number, r: number): [number, number] {
  const angle = Math.PI * (1 - t); // π → 0
  return [CX + r * Math.cos(angle), CY - r * Math.sin(angle)];
}

/** 도넛 호 SVG path (t1 ~ t2 구간) */
function arcPath(t1: number, t2: number): string {
  const [x1o, y1o] = pt(t1, R_OUT);
  const [x2o, y2o] = pt(t2, R_OUT);
  const [x1i, y1i] = pt(t1, R_IN);
  const [x2i, y2i] = pt(t2, R_IN);
  const large = t2 - t1 > 0.5 ? 1 : 0;
  return [
    `M ${x1o.toFixed(2)} ${y1o.toFixed(2)}`,
    `A ${R_OUT} ${R_OUT} 0 ${large} 1 ${x2o.toFixed(2)} ${y2o.toFixed(2)}`,
    `L ${x2i.toFixed(2)} ${y2i.toFixed(2)}`,
    `A ${R_IN} ${R_IN} 0 ${large} 0 ${x1i.toFixed(2)} ${y1i.toFixed(2)}`,
    "Z",
  ].join(" ");
}

interface Zone {
  min: number;
  max: number;
  color: string;
}

interface MacroGaugeProps {
  title: string;
  value: number | null;
  label: string | null;
  maxValue: number;
  zones: Zone[];
  prevClose?: number | null;
  weekAgo?: number | null;
  monthAgo?: number | null;
  updatedAt?: string | null;
}

export function MacroGauge({
  title,
  value,
  label,
  maxValue,
  zones,
  prevClose,
  weekAgo,
  monthAgo,
}: MacroGaugeProps) {
  // 현재값 색상 (어느 zone인지)
  const currentZone = value !== null
    ? zones.find(z => value >= z.min && value <= z.max) ?? zones[zones.length - 1]
    : null;
  const valueColor = currentZone?.color ?? "#6b7280";

  // 바늘 위치
  const needleT = value !== null ? Math.min(Math.max(value / maxValue, 0), 1) : 0.5;
  const [nx, ny] = pt(needleT, R_OUT - 10);

  return (
    <div className="flex flex-col items-center">
      <p className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-1">{title}</p>

      <svg viewBox="0 0 200 110" className="w-full max-w-[220px]">
        {/* 배경 호 (전체) */}
        <path d={arcPath(0, 1)} fill="#1f2937" />

        {/* 색상 구간 호 */}
        {zones.map((z) => {
          const t1 = z.min / maxValue;
          const t2 = z.max / maxValue;
          return (
            <path key={z.color} d={arcPath(t1, t2)} fill={z.color} opacity={0.85} />
          );
        })}

        {/* 바늘 */}
        {value !== null && (
          <>
            <line
              x1={CX} y1={CY}
              x2={nx.toFixed(2)} y2={ny.toFixed(2)}
              stroke="white" strokeWidth="2.5" strokeLinecap="round"
            />
            <circle cx={CX} cy={CY} r="5" fill="white" />
          </>
        )}

        {/* 중앙 텍스트: 현재값 */}
        <text
          x={CX} y={CY - 12}
          textAnchor="middle"
          fontSize="26"
          fontWeight="bold"
          fill={valueColor}
        >
          {value !== null ? value : "—"}
        </text>

        {/* 라벨 */}
        <text x={CX} y={CY + 6} textAnchor="middle" fontSize="9" fill={valueColor} fontWeight="600">
          {label ?? ""}
        </text>

        {/* 좌/우 끝 레이블 */}
        <text x="10" y="108" fontSize="8" fill="#6b7280">{zones[0]?.min ?? 0}</text>
        <text x="190" y="108" fontSize="8" fill="#6b7280" textAnchor="end">{maxValue}</text>
      </svg>

      {/* 이전값 비교 */}
      <div className="flex gap-4 text-center mt-1">
        {prevClose != null && (
          <div>
            <p className="text-[9px] text-gray-600">전일</p>
            <p className="text-xs font-semibold text-gray-400">{prevClose}</p>
          </div>
        )}
        {weekAgo != null && (
          <div>
            <p className="text-[9px] text-gray-600">1주전</p>
            <p className="text-xs font-semibold text-gray-400">{weekAgo}</p>
          </div>
        )}
        {monthAgo != null && (
          <div>
            <p className="text-[9px] text-gray-600">1달전</p>
            <p className="text-xs font-semibold text-gray-400">{monthAgo}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// Fear & Greed 전용 zones
export const FG_ZONES = [
  { min: 0,  max: 25,  color: "#ef4444" }, // Extreme Fear
  { min: 25, max: 45,  color: "#f97316" }, // Fear
  { min: 45, max: 55,  color: "#eab308" }, // Neutral
  { min: 55, max: 75,  color: "#84cc16" }, // Greed
  { min: 75, max: 100, color: "#22c55e" }, // Extreme Greed
];

// VIX 전용 zones
export const VIX_ZONES = [
  { min: 0,  max: 12,  color: "#22c55e" }, // Low
  { min: 12, max: 20,  color: "#84cc16" }, // Normal
  { min: 20, max: 30,  color: "#eab308" }, // Elevated
  { min: 30, max: 40,  color: "#f97316" }, // High
  { min: 40, max: 60,  color: "#ef4444" }, // Extreme
];

/** rule-based 코멘트 (매크로만) */
export function getMacroComment(
  fg: number | null,
  vix: number | null
): { text: string; color: string } {
  if (fg === null && vix === null)
    return { text: "매크로 데이터 수집 중입니다.", color: "text-gray-500" };
  if (fg !== null && fg < 20 && vix !== null && vix > 25)
    return { text: "극도 공포 + 변동성 확대 — 바닥 탐색 구간, 역발상 매수 관점 참고", color: "text-amber-400" };
  if (fg !== null && fg < 20)
    return { text: "공포 극단 구간 — 역사적으로 역발상 매수 기회였던 경우 많음", color: "text-amber-400" };
  if (fg !== null && fg > 80 && vix !== null && vix < 15)
    return { text: "과열 + 저변동성 — 차익실현 고려 구간, 신규 진입 신중히", color: "text-rose-400" };
  if (vix !== null && vix > 30)
    return { text: "변동성 급등 — 단기 포지션 관리 필요, 방어적 접근 유효", color: "text-rose-400" };
  if (fg !== null && fg > 60)
    return { text: "탐욕 구간 — 시장 낙관론 우세, 과열 여부 모니터링 필요", color: "text-yellow-400" };
  return { text: "중립 구간 — 개별 종목 및 섹터 선별에 집중할 구간", color: "text-gray-400" };
}

/** 매크로 + 컨센서스 통합 코멘트 (종목명 포함) */
export function getIntegratedComment(
  fg: number | null,
  vix: number | null,
  topBullish: Array<{ name: string; count: number }>,
  topBearish: Array<{ name: string; count: number }>
): { text: string; color: string } {
  const bullStr = topBullish.slice(0, 2).map(t => `${t.name}(${t.count}곳)`).join(', ');
  const bearStr = topBearish.slice(0, 1).map(t => `${t.name}(${t.count}곳)`).join(', ');
  const hasBull = topBullish.length > 0;
  const hasBear = topBearish.length > 0;

  if (fg === null && vix === null) {
    if (hasBull)
      return { text: `이번 주 ${bullStr} 상승 전망 집중${hasBear ? ` · ${bearStr} 약세 전망` : ''} — 섹터 선별 전략 유효`, color: "text-gray-400" };
    return { text: "매크로 데이터 수집 중입니다.", color: "text-gray-500" };
  }

  // 극도 공포 + 고변동성
  if (fg !== null && fg < 20 && vix !== null && vix > 25) {
    if (hasBull)
      return { text: `공포 극단(F&G ${fg}) + 변동성 급등(VIX ${vix}) 속에서도 ${bullStr} 상승 전망 집중 — 역발상 관점 주목`, color: "text-amber-400" };
    return { text: `극도 공포(F&G ${fg}) + 변동성 확대(VIX ${vix}) — 바닥 탐색 구간, 역발상 매수 관점 참고`, color: "text-amber-400" };
  }

  // 극도 공포만
  if (fg !== null && fg < 20) {
    if (hasBull)
      return { text: `공포 극단(F&G ${fg}) 속 ${bullStr} 상승 전망 — 역사적 역발상 매수 구간 신호`, color: "text-amber-400" };
    return { text: `공포 극단 구간(F&G ${fg}) — 역사적으로 역발상 매수 기회였던 경우 많음`, color: "text-amber-400" };
  }

  // 과열 + 저변동성
  if (fg !== null && fg > 80 && vix !== null && vix < 15) {
    if (hasBull)
      return { text: `과열 구간(F&G ${fg})에서 ${bullStr} 강세 전망 — 신규 진입 신중, 차익실현 고려`, color: "text-rose-400" };
    return { text: `과열 + 저변동성 — 차익실현 고려 구간, 신규 진입 신중히`, color: "text-rose-400" };
  }

  // 고변동성
  if (vix !== null && vix > 30) {
    if (hasBull && hasBear)
      return { text: `변동성 급등(VIX ${vix}) 속 ${bullStr} 강세 vs ${bearStr} 약세 — 방향 분산, 선별 접근 필요`, color: "text-rose-400" };
    if (hasBull)
      return { text: `변동성 급등(VIX ${vix}) 속에서도 ${bullStr} 상승 전망 — 변동성 감안 포지션 관리`, color: "text-rose-400" };
    return { text: `변동성 급등(VIX ${vix}) — 단기 포지션 관리 필요, 방어적 접근 유효`, color: "text-rose-400" };
  }

  // 탐욕
  if (fg !== null && fg > 60) {
    if (hasBull)
      return { text: `탐욕 구간(F&G ${fg})에서 ${bullStr} 강세 전망 집중 — 과열 여부 모니터링`, color: "text-yellow-400" };
    return { text: `탐욕 구간(F&G ${fg}) — 시장 낙관론 우세, 과열 여부 모니터링 필요`, color: "text-yellow-400" };
  }

  // 중립
  if (hasBull)
    return { text: `이번 주 ${bullStr} 상승 전망 집중${hasBear ? ` · ${bearStr} 약세 전망` : ''} — 섹터 선별 전략 유효`, color: "text-gray-400" };
  return { text: "중립 구간 — 개별 종목 및 섹터 선별에 집중할 구간", color: "text-gray-400" };
}
