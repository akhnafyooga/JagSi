'use client';

import { useEffect, useRef } from 'react';
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

  const nav = useRef<HTMLElement>(null);

  useEffect(() => {
    const track = nav.current;
    const active = track?.querySelector<HTMLElement>('[aria-current=page]');
    if (!track || !active) return;
    const trackBounds = track.getBoundingClientRect();
    const activeBounds = active.getBoundingClientRect();
    track.scrollLeft += activeBounds.left - trackBounds.left - (track.clientWidth - activeBounds.width) / 2;
  }, [pathname]);

  return (
    <nav ref={nav} aria-label="Navigasi utama" className="ungu-nav-track flex min-w-0 gap-1 overflow-x-auto p-1">
      {items.map((item) => {
        const active = pathname === item.href;
        const nav = useRef<HTMLElement>(null);

  useEffect(() => {
    const track = nav.current;
    const active = track?.querySelector<HTMLElement>('[aria-current=page]');
    if (!track || !active) return;
    const trackBounds = track.getBoundingClientRect();
    const activeBounds = active.getBoundingClientRect();
    track.scrollLeft += activeBounds.left - trackBounds.left - (track.clientWidth - activeBounds.width) / 2;
  }, [pathname]);

  return (
          <Link
            key={item.href}
            href={item.href} aria-current={active ? 'page' : undefined}
            className={`flex min-h-11 shrink-0 items-center gap-2 whitespace-nowrap rounded-full px-3 text-sm font-medium transition-colors md:px-4 ${
              active ? 'bg-primary-container text-on-primary-container' : 'text-white hover:bg-white/10'
            }`}
          >
            <Icon
              name={item.icon}
              filled={active}
              className="text-[19px]"
            />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
