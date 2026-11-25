import Link from 'next/link';
import { BottomNav } from './BottomNav';
import { NotificationBell } from './NotificationBell';

export function TopAppBar({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <>
      <header className="sticky top-0 z-40 border-b border-surface-container-highest bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-2 px-4 py-2">
          <Link href="/" className="text-xl font-bold text-primary">JagSi</Link>
          <BottomNav />
          <NotificationBell />
        </div>
      </header>
      <div className="mx-auto max-w-7xl px-4 pb-4 pt-8 md:pt-12">
        {subtitle && <p className="mb-2 text-sm text-on-surface-variant">{subtitle}</p>}
        <h1 className="jagsi-display text-4xl font-semibold tracking-tight md:text-6xl">{title}</h1>
      </div>
    </>
  );
}
