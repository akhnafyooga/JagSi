import { cn } from '@/lib/utils';
import { Icon } from './Icon';

interface FallStatusCardProps {
  status: string;
  label: string;
  note: string;
}

export function FallStatusCard({ status, label, note }: FallStatusCardProps) {
  return (
    <article className="rounded-2xl border border-surface-container-highest/60 bg-surface-container-lowest p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-teal-50 text-teal-700">
          <Icon name="directions_walk" className="text-[20px]" />
        </div>
        <span className="rounded-full border border-emerald-200/50 bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700">
          • Normal
        </span>
      </div>
      <div className="mt-3">
        <span className="text-xs font-medium text-on-surface-variant">{label}</span>
        <div className="mt-0.5 flex items-baseline gap-1">
          <span className={cn('text-2xl font-bold tracking-tight text-emerald-800')}>{status}</span>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between border-t border-surface-container-low pt-2 text-[11px] text-on-surface-variant/80">
        <span>{note}</span>
        <Icon name="shield" filled className="text-[16px] text-emerald-600" />
      </div>
    </article>
  );
}
