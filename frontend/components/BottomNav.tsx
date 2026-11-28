'use client';

import { useEffect, useId, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Icon } from './Icon';

const items = [
  { href: '/beranda', label: 'Beranda', icon: 'home' },
  { href: '/riwayat', label: 'Riwayat', icon: 'history' },
  { href: '/profil', label: 'Profil', icon: 'person' },
  { href: '/darurat', label: 'Darurat', icon: 'sos' },
];

export function BottomNav() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const nav = useRef<HTMLElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const listId = useId();
  const current = items.find(item => item.href === pathname) ?? items[0];

  useEffect(() => {
    if (!open) return;
    function closeOutside(event: PointerEvent) {
      if (!nav.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener('pointerdown', closeOutside);
    return () => document.removeEventListener('pointerdown', closeOutside);
  }, [open]);

  return (
    <>
    <nav aria-label="Navigasi utama" className="hidden items-center gap-1 lg:flex">
      {items.map(item => (
        <Link key={item.href} href={item.href} aria-current={item.href === pathname ? 'page' : undefined}
          className={`desktop-nav-link ${item.href === pathname ? 'bg-primary-container text-on-primary-container' : 'text-white hover:bg-white/10'}`}>
          <Icon name={item.icon} />
          {item.label}
        </Link>
      ))}
    </nav>
    <nav ref={nav} aria-label="Navigasi utama" className="relative order-first lg:hidden"
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget)) setOpen(false);
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape' && open) {
          event.preventDefault();
          setOpen(false);
          trigger.current?.focus();
        }
      }}>
      <button ref={trigger} type="button" aria-expanded={open} aria-controls={listId}
        className="ungu-nav-pill" onClick={() => setOpen(!open)}>
        <Icon name={current.icon} />
        {current.label}
        <Icon name="expand_more" className={open ? 'ungu-nav-chevron rotate-180' : 'ungu-nav-chevron'} />
      </button>
      <ul id={listId} className="ungu-nav-links" data-open={open} aria-hidden={!open}>
        {items.filter(item => item.href !== current.href).map(item => (
          <li key={item.href}>
            <Link href={item.href} tabIndex={open ? undefined : -1} className="ungu-nav-pill"
              onClick={() => setOpen(false)}>
              <Icon name={item.icon} />
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </nav>
    </>
  );
}
