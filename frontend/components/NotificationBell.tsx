'use client';

import Link from 'next/link';

import { cn } from '@/lib/utils';

import { useEmergencyAlertContext } from './EmergencyAlertsProvider';
import { Icon } from './Icon';

/**
 * The bell in the top bar. Until Week 8 its red dot was always on, whatever
 * happened; now it shows how many alerts are still waiting and opens Darurat.
 */
export function NotificationBell() {
  const ctx = useEmergencyAlertContext();
  const count = ctx?.open.length ?? 0;
  const label = count > 0 ? `Notifikasi, ${count} peringatan belum ditangani` : 'Notifikasi';

  return (
    <Link
      href="/darurat"
      aria-label={label}
      className="relative flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20 active:scale-95"
    >
      <Icon name={count > 0 ? 'notifications_active' : 'notifications'} filled={count > 0} className={cn('text-[24px]', count > 0 && 'text-rose-200')} />
      {count > 0 ? (
        <span className="absolute right-1 top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-error px-1 text-[10px] font-bold leading-none text-on-error">
          {count > 9 ? '9+' : count}
        </span>
      ) : null}
    </Link>
  );
}
