import Link from 'next/link';
import { BottomNav } from './BottomNav';
import { NotificationBell } from './NotificationBell';

export function TopAppBar({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <>
      <header className="sticky top-0 z-40 px-4 pt-4 md:px-8 md:pt-6">
        <div className="desktop-nav-shell flex w-fit max-w-full items-center gap-2">
          <Link href="/" className="ungu-nav-pill shrink-0"><span className="ungu-brand"><img src="/ungu/brand.svg" alt="" />JagSi</span></Link>
          <BottomNav />
          <NotificationBell />
        </div>
      </header>
      <div className="ungu-page-heading mx-auto max-w-[1440px] px-[var(--jagsi-gutter)] pb-8 pt-10 md:pb-10 md:pt-14">
        {subtitle && <p className="mb-3 text-sm text-on-surface-variant">{subtitle}</p>}
        <h1 className="jagsi-display text-4xl font-semibold tracking-tight md:text-6xl">{title}</h1>
      </div>
    </>
  );
}
