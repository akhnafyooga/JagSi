'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Icon } from './Icon';

const items = [
  { href: '/beranda', label: 'Beranda', icon: 'home' },
  { href: '/monitoring', label: 'Monitoring', icon: 'monitor_heart' },
  { href: '/riwayat', label: 'Riwayat', icon: 'history' },
  { href: '/profil', label: 'Profil', icon: 'person' },
  { href: '/darurat', label: 'Darurat', icon: 'sos' },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="flex flex-wrap gap-1 border-y border-surface-container-highest bg-white px-3 md:border-0">
      {items.map((item) => {
        const active = pathname === item.href;
        return (
          <Link
            key={item.href}
            href={item.href} aria-current={active ? 'page' : undefined}
            className={`flex min-h-11 items-center gap-1 rounded-xl px-2 text-xs font-medium transition-colors md:px-4 md:text-sm ${
              active ? 'bg-primary-container text-primary' : 'text-on-surface-variant'
            }`}
          >
            <Icon
              name={item.icon}
              filled={active}
              className={`text-[22px] ${active ? 'bg-primary-container text-primary' : ''}`}
            />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
