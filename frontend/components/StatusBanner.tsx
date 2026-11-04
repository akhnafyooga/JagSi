import type { VitalTone } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Icon } from './Icon';

const toneStyles: Record<VitalTone, { box: string; badge: string; icon: string; text: string; glyph: string }> = {
  normal: {
    box: 'border-emerald-200/70 bg-emerald-50/80',
    badge: 'bg-emerald-200/60 text-emerald-700',
    icon: 'bg-emerald-100 text-emerald-700',
    text: 'text-emerald-950',
    glyph: 'verified_user',
  },
  warning: {
    box: 'border-amber-200/70 bg-amber-50/80',
    badge: 'bg-amber-200/60 text-amber-700',
    icon: 'bg-amber-100 text-amber-700',
    text: 'text-amber-950',
    glyph: 'warning',
  },
  critical: {
    box: 'border-error/30 bg-error/10',
    badge: 'bg-error-container/60 text-on-error-container',
    icon: 'bg-error-container text-on-error-container',
    text: 'text-error',
    glyph: 'emergency',
  },
};

interface StatusBannerProps {
  tone: VitalTone;
  title: string;
  message?: string;
  badge?: string;
}

export function StatusBanner({ tone, title, message, badge }: StatusBannerProps) {
  const s = toneStyles[tone];
  return (
    <section className={cn('flex items-start gap-3 rounded-2xl border p-3.5 shadow-sm', s.box)}>
      <div className={cn('mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full', s.icon)}>
        <Icon name={s.glyph} filled className="text-[22px]" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <h2 className={cn('text-sm font-semibold', s.text)}>{title}</h2>
          {badge ? (
            <span className={cn('rounded-md px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider', s.badge)}>
              {badge}
            </span>
          ) : null}
        </div>
        {message ? <p className="mt-0.5 text-xs text-on-surface-variant">{message}</p> : null}
      </div>
    </section>
  );
}
