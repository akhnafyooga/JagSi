import type { Vital } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Icon } from './Icon';

const toneChip: Record<Vital['tone'], string> = {
  normal: 'bg-emerald-50 text-emerald-700 border-emerald-200/50',
  warning: 'bg-amber-50 text-amber-700 border-amber-200/50',
  critical: 'bg-error/10 text-error border-error/30',
};

const toneIcon: Record<Vital['tone'], string> = {
  normal: 'bg-rose-50 text-rose-500',
  warning: 'bg-amber-50 text-amber-600',
  critical: 'bg-error/10 text-error',
};

export function VitalCard({ vital }: { vital: Vital }) {
  return (
    <article className="rounded-2xl border border-surface-container-highest/60 bg-surface-container-lowest p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className={cn('flex h-9 w-9 items-center justify-center rounded-xl', toneIcon[vital.tone])}>
          <Icon name={vital.icon} className="text-[20px]" />
        </div>
        <span
          className={cn(
            'rounded-full border px-2 py-0.5 text-xs font-semibold',
            toneChip[vital.tone],
          )}
        >
          {vital.statusLabel}
        </span>
      </div>
      <div className="mt-3">
        <span className="text-xs font-medium text-on-surface-variant">{vital.label}</span>
        <div className="mt-0.5 flex items-baseline gap-1">
          <span className="text-2xl font-bold tracking-tight text-on-surface">{vital.value}</span>
          <span className="text-sm font-medium text-on-surface-variant">{vital.unit}</span>
        </div>
      </div>
      <div className="mt-2 border-t border-surface-container-low pt-2 text-[11px] text-on-surface-variant/80">
        {vital.note}
      </div>
    </article>
  );
}
