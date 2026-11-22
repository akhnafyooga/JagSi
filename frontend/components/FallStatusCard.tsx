import { cn } from '@/lib/utils';
import { Icon } from './Icon';

export type FallTone = 'normal' | 'critical' | 'unknown';

interface FallStatusCardProps {
  status: string;
  label: string;
  note: string;
  /** Week 8: the card now reflects live alerts instead of always showing "Normal". */
  tone?: FallTone;
}

const TONES: Record<FallTone, { chip: string; chipText: string; status: string; icon: string; glyph: string; iconBox: string }> = {
  normal: {
    chip: 'border-emerald-200/50 bg-emerald-50 text-emerald-700',
    chipText: '• Normal',
    status: 'text-emerald-800',
    icon: 'text-emerald-600',
    glyph: 'shield',
    iconBox: 'bg-teal-50 text-teal-700',
  },
  critical: {
    chip: 'border-error/30 bg-error/10 text-error',
    chipText: '• Darurat',
    status: 'text-error',
    icon: 'text-error',
    glyph: 'emergency',
    iconBox: 'bg-error/10 text-error',
  },
  unknown: {
    chip: 'border-surface-container-highest bg-surface-container-high text-on-surface-variant',
    chipText: '• Tidak diketahui',
    status: 'text-on-surface-variant',
    icon: 'text-on-surface-variant',
    glyph: 'help',
    iconBox: 'bg-surface-container-high text-on-surface-variant',
  },
};

export function FallStatusCard({ status, label, note, tone = 'normal' }: FallStatusCardProps) {
  const t = TONES[tone];
  return (
    <article className="rounded-2xl border border-surface-container-highest/60 bg-surface-container-lowest p-4 shadow-sm">
      <div className="flex items-center justify-between">
        <div className={cn('flex h-9 w-9 items-center justify-center rounded-xl', t.iconBox)}>
          <Icon name={tone === 'critical' ? 'personal_injury' : 'directions_walk'} className="text-[20px]" />
        </div>
        <span className={cn('rounded-full border px-2 py-0.5 text-xs font-semibold', t.chip)}>{t.chipText}</span>
      </div>
      <div className="mt-3">
        <span className="text-xs font-medium text-on-surface-variant">{label}</span>
        <div className="mt-0.5 flex items-baseline gap-1">
          <span className={cn('text-2xl font-bold tracking-tight', t.status)}>{status}</span>
        </div>
      </div>
      <div className="mt-2 flex items-center justify-between border-t border-surface-container-low pt-2 text-[11px] text-on-surface-variant/80">
        <span>{note}</span>
        <Icon name={t.glyph} filled className={cn('text-[16px]', t.icon)} />
      </div>
    </article>
  );
}
