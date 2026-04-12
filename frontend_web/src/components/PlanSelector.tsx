'use client';

import { useState } from 'react';
import { PLANS } from '@/lib/plans';

interface PlanSelectorProps {
  onClose: () => void;
  isRenewal?: boolean;
  currentExpiresAt?: string | null; // ISO string
}

export function PlanSelector({ onClose, isRenewal = false, currentExpiresAt }: PlanSelectorProps) {
  const [selected, setSelected] = useState<string>('annual');
  const [loading, setLoading] = useState(false);

  const activePlans = Object.values(PLANS);

  // 연장 시 선택한 플랜 기준 새 만료일 계산
  const calcNewExpiry = (planId: string): string | null => {
    if (!isRenewal || !PLANS[planId]) return null;
    const base = currentExpiresAt && new Date(currentExpiresAt) > new Date()
      ? new Date(currentExpiresAt)
      : new Date();
    const next = new Date(base);
    next.setMonth(next.getMonth() + PLANS[planId].months);
    return next.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' });
  };

  const handlePayment = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/payment/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ planId: selected }),
      });
      const data = await res.json();
      if (data.payurl) {
        window.location.href = data.payurl;
      } else {
        alert('결제 요청 실패: ' + (data.error || '알 수 없는 오류'));
        setLoading(false);
      }
    } catch {
      alert('오류가 발생했습니다. 다시 시도해주세요.');
      setLoading(false);
    }
  };

  return (
    /* 모달 오버레이 */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-full max-w-md bg-[#111115] border border-white/10 rounded-3xl p-8 shadow-2xl">
        {/* 헤더 */}
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-bold">{isRenewal ? '구독 연장' : '플랜 선택'}</h3>
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
          >
            ✕
          </button>
        </div>

        {/* 플랜 카드 목록 */}
        <div className="space-y-3 mb-6">
          {activePlans.map((plan) => (
            <button
              key={plan.id}
              onClick={() => setSelected(plan.id)}
              className={`w-full text-left p-5 rounded-2xl border transition-all ${
                selected === plan.id
                  ? 'border-purple-500 bg-purple-500/10'
                  : 'border-white/10 bg-white/[0.03] hover:border-white/20'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div
                    className={`w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 ${
                      selected === plan.id ? 'border-purple-400' : 'border-gray-600'
                    }`}
                  >
                    {selected === plan.id && (
                      <div className="w-2 h-2 rounded-full bg-purple-400" />
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm">{plan.label}</span>
                      {plan.badge && (
                        <span className="text-[10px] px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded-full font-bold whitespace-nowrap">
                          {plan.badge}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5 pr-2 leading-relaxed">{plan.description}</p>
                  </div>
                </div>
                <div className="flex flex-col items-end shrink-0">
                  {plan.originalPrice && (
                    <span className="text-[10px] text-gray-500 line-through mb-0.5">
                      {plan.originalPrice.toLocaleString()}원
                    </span>
                  )}
                  <span
                    className={`text-sm font-bold ${
                      selected === plan.id ? 'text-purple-300' : 'text-gray-400'
                    }`}
                  >
                    {plan.priceLabel}
                  </span>
                </div>
              </div>
            </button>
          ))}
        </div>

        {/* 선택 플랜 요약 */}
        {selected && PLANS[selected] && (
          <div className="mb-6 p-4 rounded-2xl bg-black/40 border border-white/5 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">{PLANS[selected].name}</span>
              <span className="font-bold text-white">
                {PLANS[selected].price.toLocaleString()}원
              </span>
            </div>
            {isRenewal && calcNewExpiry(selected) && (
              <div className="flex items-center gap-1.5 text-xs text-emerald-400">
                <span>📅</span>
                <span>{calcNewExpiry(selected)}까지 연장됩니다</span>
              </div>
            )}
          </div>
        )}

        {/* 결제 버튼 */}
        <button
          onClick={handlePayment}
          disabled={loading || !selected}
          className="w-full py-4 bg-gradient-to-r from-purple-600 to-blue-600 text-white font-bold rounded-2xl hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
        >
          {loading ? (
            <>
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              결제 페이지 이동 중...
            </>
          ) : (
            '결제하기'
          )}
        </button>

        <p className="text-center text-xs text-gray-600 mt-4">
          페이앱을 통한 안전한 결제 · 결제 후 즉시 구독 활성화
        </p>
      </div>
    </div>
  );
}
