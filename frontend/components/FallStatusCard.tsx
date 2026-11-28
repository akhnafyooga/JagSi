import { cn } from '@/lib/utils';
import { Icon } from './Icon';

export type FallTone = 'normal' | 'critical' | 'unknown';

interface FallStatusCardProps {
  status: string;
  label: string;
  note: string;
  /** Week 8: the card now reflects live alerts instead of always showing "Normal". */
  tone?: FallTone;
  emergency?: boolean;
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

export function FallStatusCard({ status, label, note, tone = 'normal', emergency = false }: FallStatusCardProps) {
  const t = TONES[tone];
  return (
    <article className={emergency ? "ungu-heart ungu-stack" : "ungu-panel ungu-fall"}>
      <small>{label} · {t.chipText}</small>
      <h2 className={tone === 'critical' ? 'text-error' : ''}>{status}</h2>
      <p>{note}</p>
      <a className="ungu-action" href={emergency ? "#log-kejadian" : "/darurat"}>{emergency ? "Lihat log kejadian" : "Lihat peringatan"}</a>
    </article>
  );
}
