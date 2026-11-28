import Link from 'next/link';
import { BottomNav } from './BottomNav';
import { NotificationBell } from './NotificationBell';

export function TopAppBar({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <>
      <header className="sticky top-0 z-40 px-4 pt-4 md:px-8 md:pt-6">
        <div className="ungu-navbar mx-auto flex w-fit max-w-full items-center gap-2 rounded-full p-2">
          <Link href="/" className="shrink-0 rounded-full bg-white/10 px-3 py-3 text-sm font-bold text-white"><span className="ungu-brand"><img src="/ungu/brand.svg" alt="" />JagSi</span></Link>
          <BottomNav />
          <NotificationBell />
        </div>
      </header>
      <div className="mx-auto max-w-[1440px] px-[var(--jagsi-gutter)] pb-8 pt-10 md:pb-10 md:pt-14">
        {subtitle && <p className="mb-3 text-sm text-on-surface-variant">{subtitle}</p>}
        <h1 className="jagsi-display text-4xl font-semibold tracking-tight md:text-6xl">{title}</h1>
      </div>
    </>
  );
}
