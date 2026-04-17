'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const items = [
  { href: '/dashboard',  icon: '📊', label: '대시보드',  id: 'tour-nav-dashboard' },
  { href: '/consensus',  icon: '🧭', label: '컨센서스',  id: 'tour-nav-consensus' },
  { href: '/history',    icon: '🎯', label: '성과',      id: 'tour-nav-history' },
  { href: '/trump',      icon: '🏛️', label: '트럼프',    id: 'tour-nav-trump' },
  { href: '/referrals',  icon: '🎁', label: '초대',      id: 'tour-nav-referrals' },
  { href: '/settings',   icon: '⚙️', label: '설정',      id: 'tour-nav-settings' },
];

export function MobileNav() {
  const pathname = usePathname();
  return (
    <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-[#0e0e11]/95 backdrop-blur-xl border-t border-white/10">
      <div className="flex items-center justify-around px-2 py-3 pb-[env(safe-area-inset-bottom,12px)]">
        {items.map(({ href, icon, label, id }) => {
          const active = pathname === href;
          return (
            <Link key={href} href={href} id={id}
              className={`flex flex-col items-center gap-1 px-2 py-1 rounded-xl transition-colors ${
                active ? 'text-purple-400' : 'text-gray-500'
              }`}>
              <span className="text-xl">{icon}</span>
              <span className="text-[10px] font-semibold">{label}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
