'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface DashboardSidebarProps {
  user: {
    name?: string | null;
    email?: string | null;
    image?: string | null;
  };
}

const navItems = [
  { href: '/dashboard', icon: '📊', label: '대시보드' },
  { href: '/referrals', icon: '🎁', label: '초대 혜택' },
  { href: '/settings', icon: '⚙️', label: '설정' },
];

export function DashboardSidebar({ user }: DashboardSidebarProps) {
  const pathname = usePathname();

  return (
    <aside className="w-64 border-r border-white/5 bg-white/[0.01] flex flex-col p-6 shrink-0">
      <div className="flex items-center gap-2 mb-12">
        <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-600 rounded-lg flex items-center justify-center font-bold text-sm">
          S
        </div>
        <span className="text-lg font-bold">StockNow</span>
      </div>

      <nav className="flex-1 space-y-2">
        {navItems.map(({ href, icon, label }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-4 py-3 rounded-xl font-medium transition-all group ${
                isActive
                  ? 'bg-white/5 text-purple-400'
                  : 'hover:bg-white/5 text-gray-400'
              }`}
            >
              <span
                className={`p-1.5 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-purple-500/20 group-hover:bg-purple-500/30'
                    : 'bg-white/5 group-hover:bg-white/10'
                }`}
              >
                {icon}
              </span>
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto pt-6 border-t border-white/5">
        <div className="flex items-center gap-3 px-2">
          {user.image ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={user.image}
              alt="profile"
              className="w-10 h-10 rounded-full border border-white/10 object-cover"
            />
          ) : (
            <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-gray-700 to-gray-500 border border-white/10" />
          )}
          <div>
            <div className="text-sm font-semibold">{user.name || '사용자'}</div>
            <div className="text-xs text-gray-500 line-clamp-1">{user.email || ''}</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
