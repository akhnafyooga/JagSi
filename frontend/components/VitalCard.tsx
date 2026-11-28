import type { Vital } from '@/lib/types';
import { cn } from '@/lib/utils';
import { Icon } from './Icon';

const toneChip: Record<Vital['tone'], string> = {
  normal: 'bg-primary-container text-on-primary-container border-transparent',
  warning: 'bg-amber-50 text-amber-700 border-amber-200/50',
  critical: 'bg-error/10 text-error border-error/30',
};

const toneIcon: Record<Vital['tone'], string> = {
  normal: 'bg-primary-container text-primary',
  warning: 'bg-amber-50 text-amber-600',
  critical: 'bg-error/10 text-error',
};

export function VitalCard({ vital }: { vital: Vital }) {
  return (
    <article className="ungu-panel min-w-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
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
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs font-medium text-on-surface-variant">{vital.label}</span>
          {vital.simulated ? (
            <span
              title="Nilai berasal dari simulasi Wokwi, bukan sensor sebenarnya"
              className="rounded border border-on-surface-variant/30 px-1 text-[9px] font-semibold uppercase tracking-wider text-on-surface-variant"
            >
              Sim
            </span>
          ) : null}
        </div>
        <div className="mt-0.5 flex items-baseline gap-1">
          <span className="jagsi-display text-3xl font-semibold tracking-tight text-on-surface">
            {vital.value === null ? '--' : vital.value}
          </span>
          <span className="text-sm font-medium text-on-surface-variant">{vital.unit}</span>
        </div>
      </div>
      <div className="border-t border-surface-container-highest pt-2 text-[11px] text-on-surface-variant/80">
        {vital.note}
      </div>
    </article>
  );
}
