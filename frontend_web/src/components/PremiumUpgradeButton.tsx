'use client';

import { useState } from 'react';
import { PlanSelector } from './PlanSelector';

export function PremiumUpgradeButton({ isRenewal = false, expiresAt }: { isRenewal?: boolean; expiresAt?: string | null }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="w-full sm:w-auto px-6 py-3 bg-white text-black font-bold rounded-2xl hover:scale-105 transition-transform flex items-center justify-center gap-2"
      >
        {isRenewal ? '🔄 구독 연장하기' : '⭐ 프리미엄 업그레이드'}
      </button>

      {open && <PlanSelector onClose={() => setOpen(false)} isRenewal={isRenewal} currentExpiresAt={expiresAt} />}
    </>
  );
}
