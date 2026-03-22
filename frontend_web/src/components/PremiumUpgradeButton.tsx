'use client';

import { useState } from 'react';
import { PlanSelector } from './PlanSelector';

export function PremiumUpgradeButton() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        className="px-6 py-3 bg-white text-black font-bold rounded-2xl hover:scale-105 transition-transform"
      >
        프리미엄 업그레이드
      </button>

      {open && <PlanSelector onClose={() => setOpen(false)} />}
    </>
  );
}
