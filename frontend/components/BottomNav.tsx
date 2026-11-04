'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Icon } from './Icon';

const items = [
  { href: '/', label: 'Beranda', icon: 'home' },
  { href: '/monitoring', label: 'Monitoring', icon: 'monitor_heart' },
  { href: '/riwayat', label: 'Riwayat', icon: 'history' },
  { href: '/profil', label: 'Profil', icon: 'person' },
  { href: '/darurat', label: 'Darurat', icon: 'sos' },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed inset-x-0 bottom-0 z-40 mx-auto flex max-w-[430px] border-t border-surface-container-highest bg-surface/95 px-2 pb-[env(safe-area-inset-bottom)] backdrop-blur-md">
      {items.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href}
            className={`flex flex-1 flex-col items-center gap-0.5 py-2 text-[11px] font-medium transition-colors ${
              active ? 'text-primary' : 'text-on-surface-variant'
            }`}
          >
            <Icon
              name={item.icon}
              filled={active}
              className={`text-[22px] ${active ? 'text-primary' : ''}`}
            />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
