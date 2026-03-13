'use client';

import { useState } from 'react';

export function PremiumUpgradeButton() {
  const [loading, setLoading] = useState(false);

  const handleUpgrade = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/payment/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ planId: 'premium_1m' }), // Default to 1 month
      });
      
      const data = await res.json();
      
      if (data.payurl) {
        // Redirect to Payapp payment page
        window.location.href = data.payurl;
      } else {
        alert('결제 요청에 실패했습니다: ' + (data.error || '알 수 없는 오류'));
      }
    } catch (error) {
      console.error('Failed to request payment:', error);
      alert('오류가 발생했습니다.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      onClick={handleUpgrade}
      disabled={loading}
      className="px-6 py-3 bg-white text-black font-bold rounded-2xl hover:scale-105 transition-transform disabled:opacity-50"
    >
      {loading ? (
        <span className="w-5 h-5 border-2 border-black/30 border-t-black rounded-full animate-spin inline-block mx-4" />
      ) : (
        "프리미엄 업그레이드"
      )}
    </button>
  );
}
