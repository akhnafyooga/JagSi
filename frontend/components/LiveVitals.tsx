'use client';

import { overallTone, formatTimestamp } from '@/lib/api';
import { useLiveVitals } from '@/lib/useLiveVitals';
import { cn } from '@/lib/utils';

import { Icon } from './Icon';
import { StatusBanner } from './StatusBanner';
import { VitalCard } from './VitalCard';

const BANNER_TITLE = {
  normal: 'Semua Tanda Vital Normal',
  warning: 'Ada Tanda Vital yang Perlu Perhatian',
  critical: 'Tanda Vital di Luar Batas Aman',
} as const;

const CONNECTION_CHIP = {
  connecting: { label: 'Menghubungkan', style: 'bg-surface-container-high text-on-surface-variant' },
  live: { label: 'Live', style: 'bg-emerald-100 text-emerald-700' },
  stale: { label: 'Tertunda', style: 'bg-amber-100 text-amber-700' },
  offline: { label: 'Data Demo', style: 'bg-surface-container-high text-on-surface-variant' },
} as const;

/**
 * The live half of the dashboard.
 *
 * Kept as a separate client component so the page around it stays a server
 * component. The connection state is shown on purpose: a caregiver must be able
 * to tell a reassuring reading from a reading that simply stopped arriving.
 */
export function LiveVitals() {
  const { connection, vitals, usingMockData, lastUpdate, deviceState, error } = useLiveVitals();
  const chip = CONNECTION_CHIP[connection];
  const tone = usingMockData ? 'normal' : overallTone(vitals);

  let message: string;
  if (usingMockData) {
    message = 'Backend belum terhubung. Angka di bawah adalah data contoh, bukan data perangkat.';
  } else if (connection === 'stale') {
    message = `Data terakhir ${lastUpdate ? formatTimestamp(lastUpdate) : 'tidak diketahui'}. Aliran langsung sedang terputus.`;
  } else {
    message = `Data terakhir diperbarui ${lastUpdate ? formatTimestamp(lastUpdate) : '--:--'}`;
  }

  return (
    <>
      <StatusBanner
        tone={tone}
        title={usingMockData ? 'Mode Data Demo' : BANNER_TITLE[tone]}
        badge={usingMockData ? 'Demo' : 'Terpantau'}
        message={message}
      />

      <section className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-base font-semibold tracking-tight text-on-surface">
            Live Vital Signs
          </h2>
          <div className="flex items-center gap-1.5">
            {deviceState ? (
              <span className="text-[11px] text-on-surface-variant">
                Perangkat {deviceState === 'online' ? 'aktif' : 'tidak aktif'}
              </span>
            ) : null}
            <span
              title={error ?? undefined}
              className={cn(
                'inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider',
                chip.style,
              )}
            >
              <Icon
                name={connection === 'live' ? 'sensors' : 'sensors_off'}
                className="text-[12px]"
              />
              {chip.label}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {vitals.map((vital) => (
            <VitalCard key={vital.id} vital={vital} />
          ))}
        </div>

        <p className="pt-0.5 text-[11px] leading-snug text-on-surface-variant/80">
          Indikator, bukan diagnosis. Rentang acuan bersifat umum dan belum divalidasi klinis
          untuk lansia.
        </p>
      </section>
    </>
  );
}
