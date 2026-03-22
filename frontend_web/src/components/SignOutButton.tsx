'use client';

import { signOut } from 'next-auth/react';

export function SignOutButton() {
  return (
    <button
      onClick={() => signOut({ callbackUrl: '/auth/signin' })}
      className="w-full px-4 py-3 rounded-xl text-left text-red-400 hover:bg-red-500/10 font-medium transition-colors flex items-center gap-3"
    >
      <span className="p-1.5 bg-red-500/10 rounded-lg">🚪</span>
      로그아웃
    </button>
  );
}
