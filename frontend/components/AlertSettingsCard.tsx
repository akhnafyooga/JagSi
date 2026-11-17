'use client';

import { cn } from '@/lib/utils';

import { useEmergencyAlertContext } from './EmergencyAlertsProvider';
import { Icon } from './Icon';

const CONNECTION = {
  connecting: { label: 'Menghubungkan…', style: 'bg-surface-container-high text-on-surface-variant' },
  live: { label: 'Terhubung', style: 'bg-emerald-100 text-emerald-700' },
  reconnecting: { label: 'Menyambung ulang', style: 'bg-amber-100 text-amber-700' },
  unsupported: { label: 'Tidak didukung', style: 'bg-surface-container-high text-on-surface-variant' },
} as const;

/**
 * Lets the caregiver turn on the alarm sound and system notifications.
 *
 * Browsers block sound and notification prompts until the user clicks
 * something, so this cannot happen automatically. `compact` is the one-line
 * version shown on the home page until it has been done once.
 */
export function AlertSettingsCard({ compact = false }: { compact?: boolean }) {
  const ctx = useEmergencyAlertContext();
  if (!ctx) return null;

  const ready = ctx.soundReady && ctx.notifications !== 'default';
  if (compact && ready) return null;

  const conn = CONNECTION[ctx.connection];

  if (compact) {
    return (
      <button
        type="button"
        onClick={() => void ctx.enableAlerts()}
        className="flex w-full items-center gap-3 rounded-2xl border border-amber-300/70 bg-amber-50 p-3 text-left"
      >
        <Icon name="notifications_active" className="text-[22px] text-amber-700" />
        <span className="flex-1 text-xs text-amber-950">
          <strong className="block text-sm">Aktifkan alarm darurat</strong>
          Supaya HP berbunyi saat Ibu jatuh atau menekan SOS.
        </span>
        <Icon name="chevron_right" className="text-[20px] text-amber-700" />
      </button>
    );
  }

  return (
    <section className="space-y-3 rounded-2xl border border-surface-container-highest/60 bg-surface-container-lowest p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-on-surface">Peringatan real-time</h2>
        <span className={cn('rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider', conn.style)}>
          {conn.label}
        </span>
      </div>

      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-on-surface-variant">
          <strong className="block text-sm text-on-surface">Suara alarm</strong>
          {ctx.soundReady ? 'Siap berbunyi saat ada peringatan.' : 'Belum diaktifkan di browser ini.'}
        </div>
        <label className="relative inline-flex cursor-pointer items-center">
          <input
            type="checkbox"
            className="peer sr-only"
            aria-label="Suara alarm"
            checked={ctx.soundOn}
            onChange={(e) => ctx.setSoundOn(e.target.checked)}
          />
          <span className="h-6 w-11 rounded-full bg-surface-container-highest transition-colors peer-checked:bg-primary" />
          <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform peer-checked:translate-x-5" />
        </label>
      </div>

      <div className="text-xs text-on-surface-variant">
        <strong className="block text-sm text-on-surface">Notifikasi sistem</strong>
        {ctx.notifications === 'granted' && 'Aktif. Peringatan muncul walau tab ini tidak dibuka.'}
        {ctx.notifications === 'denied' && 'Diblokir. Izinkan notifikasi untuk situs ini di pengaturan browser.'}
        {ctx.notifications === 'default' && 'Belum diizinkan.'}
        {ctx.notifications === 'unsupported' && 'Browser ini tidak mendukung notifikasi.'}
      </div>

      {!ready ? (
        <button
          type="button"
          onClick={() => void ctx.enableAlerts()}
          className="w-full rounded-xl bg-primary py-2.5 text-sm font-semibold text-on-primary"
        >
          Aktifkan suara &amp; notifikasi
        </button>
      ) : null}
    </section>
  );
}
