// 결제 가능한 플랜 목록 — 새 플랜 추가 시 여기만 수정하면 됩니다.
// plan_id : Payapp var2로 전달되는 상품 식별자 (DB payments.plan_id)
// plan    : subscriptions.plan에 반영될 값

export interface PlanConfig {
  id: string;
  name: string;       // Payapp 상품명
  price: number;      // 결제 금액 (원)
  months: number;     // 구독 연장 개월 수
  plan: string;       // subscriptions.plan 값
  label: string;      // UI 표시 라벨
  priceLabel: string; // UI 가격 표시
  originalPrice?: number; // 정가 (옵션, 할인 표시용)
  badge?: string;     // 할인 뱃지 (옵션)
  description: string;
}

export const PLANS: Record<string, PlanConfig> = {
  // ── 현재 판매 중 ─────────────────────────────────────────────
  monthly: {
    id: "monthly",
    name: "Stock Now Standard (1개월)",
    price: 5900,
    months: 1,
    plan: "standard",
    label: "월간",
    priceLabel: "5,900원/월",
    description: "한국장 + 미국장 고래 수급 알림 전체 이용",
  },
  annual: {
    id: "annual",
    name: "Stock Now Standard (1년)",
    price: 36000,
    originalPrice: 70800,
    months: 12,
    plan: "standard",
    label: "연간",
    priceLabel: "36,000원/년",
    badge: "49% 할인",
    description: "한국장 + 미국장 고래 수급 알림 전체 이용 (월 3,000원)",
  },

  // ── 확장 예정 (활성화만 하면 즉시 판매 가능) ────────────────────
  // monthly_kr: {
  //   id: "monthly_kr",
  //   name: "Stock Now KR Only (1개월)",
  //   price: 3900,
  //   months: 1,
  //   plan: "standard_kr",
  //   label: "한국장 전용",
  //   priceLabel: "3,900원/월",
  //   description: "국내 고래 수급 알림만 이용",
  // },
  // monthly_us: {
  //   id: "monthly_us",
  //   name: "Stock Now US Only (1개월)",
  //   price: 3900,
  //   months: 1,
  //   plan: "standard_us",
  //   label: "미국장 전용",
  //   priceLabel: "3,900원/월",
  //   description: "미국 고래 수급 알림만 이용",
  // },
  // premium_monthly: {
  //   id: "premium_monthly",
  //   name: "Stock Now Premium (1개월)",
  //   price: 9900,
  //   months: 1,
  //   plan: "premium",
  //   label: "프리미엄",
  //   priceLabel: "9,900원/월",
  //   badge: "AI 분석 포함",
  //   description: "Standard 전체 + Gemini AI 심층 분석 리포트",
  // },
};

export type PlanId = keyof typeof PLANS;
