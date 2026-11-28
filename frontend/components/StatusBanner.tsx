import type { VitalTone } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Icon } from './Icon';

const toneStyles: Record<VitalTone, { box: string; badge: string; icon: string; text: string; glyph: string }> = {
  normal: {
    box: 'border-surface-container-highest bg-white',
    badge: 'bg-primary-container text-on-primary-container',
    icon: 'bg-primary-container text-primary',
    text: 'text-on-surface',
    glyph: 'verified_user',
  },
  warning: {
    box: 'border-surface-container-highest bg-white',
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
    <section className={cn('my-6 flex items-start gap-3 rounded-[20px] border p-5', s.box)}>
      <div className={cn('mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full', s.icon)}>
        <Icon name={s.glyph} filled className="text-[22px]" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className={cn('text-sm font-semibold', s.text)}>{title}</h2>
          {badge ? (
            <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider', s.badge)}>
              {badge}
            </span>
          ) : null}
        </div>
        {message ? <p className="mt-0.5 text-xs text-on-surface-variant">{message}</p> : null}
      </div>
    </section>
  );
}
