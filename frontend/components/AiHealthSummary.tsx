import { Icon } from './Icon';

interface AiHealthSummaryProps {
  text: string;
  /** Where the text came from, e.g. "Gemini · gemini-3.8-flash" or "Data demo". */
  model: string;
  updatedAt: string;
  loading?: boolean;
  /** Shows a short note that some numbers behind the summary are simulated. */
  simulated?: boolean;
  onRefresh?: () => void;
}

export function AiHealthSummary({
  text,
  model,
  updatedAt,
  loading = false,
  simulated = false,
  onRefresh,
}: AiHealthSummaryProps) {
  return (
    <section className="space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-1.5 text-base font-semibold tracking-tight text-on-surface">
          AI Health Summary
        </h2>
        <span className="flex items-center gap-1 text-xs font-semibold text-tertiary">
          <Icon name="auto_awesome" className="text-[16px]" />
          {model}
        </span>
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-tertiary-container bg-gradient-to-br from-tertiary-container/30 via-surface-container-lowest to-secondary-container/30 p-4 shadow-sm">
        <div className="mb-2.5 flex items-center justify-between">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-tertiary px-2.5 py-1 text-xs text-on-tertiary shadow-sm">
            <Icon name="psychology" className="text-[14px]" />
            JagSi AI Insight
          </span>
          <span className="flex items-center gap-1 text-xs text-on-surface-variant">
            {updatedAt}
            {onRefresh && (
              <button
                type="button"
                onClick={onRefresh}
                disabled={loading}
                aria-label="Perbarui ringkasan"
                className="flex h-6 w-6 items-center justify-center rounded-full transition-colors hover:bg-surface-container disabled:opacity-50"
              >
                <Icon name="refresh" className={`text-[16px] ${loading ? 'animate-spin' : ''}`} />
              </button>
            )}
          </span>
        </div>
        <p aria-live="polite" className="text-sm font-normal leading-relaxed text-on-surface">
          {text}
        </p>
        {simulated && (
          <p className="mt-2 text-xs text-on-surface-variant">
            Detak jantung dan SpO2 masih data simulasi, belum dari sensor asli.
          </p>
        )}
        <div className="mt-4 flex items-center justify-between gap-2 border-t border-surface-container-highest/60 pt-3">
          <button
            type="button"
            className="flex flex-1 items-center justify-center gap-1.5 rounded-xl border border-outline-variant/40 bg-surface-container-lowest px-3 py-2.5 text-xs font-semibold text-on-surface transition-colors hover:bg-surface-container active:scale-95"
          >
            Laporan Harian Komprehensif
          </button>
          <button
            aria-label="Lihat Riwayat Kesehatan"
            type="button"
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-secondary-container text-on-secondary-container transition-colors hover:bg-secondary-container/70 active:scale-95"
          >
            <Icon name="arrow_forward" className="text-[20px]" />
          </button>
        </div>
      </div>
    </section>
  );
}
