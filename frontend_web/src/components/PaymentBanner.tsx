'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

export function PaymentBanner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [banner, setBanner] = useState<'success' | 'cancel' | null>(null);

  useEffect(() => {
    const payment = searchParams.get('payment');
    if (payment === 'success') setBanner('success');
    else if (payment === 'cancel') setBanner('cancel');
  }, [searchParams]);

  const dismiss = () => {
    setBanner(null);
    // URL에서 payment 쿼리 파라미터 제거
    router.replace('/dashboard', { scroll: false });
  };

  if (!banner) return null;

  return (
    <div
      className={`mb-6 flex items-center justify-between px-6 py-4 rounded-2xl border ${
        banner === 'success'
          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          : 'bg-gray-500/10 border-gray-500/30 text-gray-400'
      }`}
    >
      <div className="flex items-center gap-3">
        <span className="text-xl">{banner === 'success' ? '🎉' : '↩️'}</span>
        <div>
          {banner === 'success' ? (
            <>
              <p className="font-semibold">결제가 완료되었습니다!</p>
              <p className="text-xs opacity-70 mt-0.5">
                구독이 활성화되었습니다. 잠시 후 새로고침하면 만료일이 업데이트됩니다.
              </p>
            </>
          ) : (
            <>
              <p className="font-semibold">결제가 취소되었습니다.</p>
              <p className="text-xs opacity-70 mt-0.5">
                언제든지 다시 업그레이드할 수 있습니다.
              </p>
            </>
          )}
        </div>
      </div>
      <button
        onClick={dismiss}
        className="ml-4 text-lg opacity-50 hover:opacity-100 transition-opacity"
      >
        ✕
      </button>
    </div>
  );
}
