'use client';

import { overallTone, formatTimestamp } from '@/lib/api';
import { useLiveVitals } from '@/lib/useLiveVitals';
import { useEffect, useState } from 'react';
import { fetchHistory, type HistoryPoint } from '@/lib/api';
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
  const tone = connection === 'stale' ? 'warning' : usingMockData ? 'normal' : overallTone(vitals);

  let message: string;
  if (usingMockData) {
    message = 'Backend belum terhubung. Angka di bawah adalah data contoh, bukan data perangkat.';
  } else if (connection === 'stale') {
    message = `Data terakhir ${lastUpdate ? formatTimestamp(lastUpdate) : 'tidak diketahui'}. Menunggu pembacaan terbaru.`;
  } else {
    message = `Data terakhir diperbarui ${lastUpdate ? formatTimestamp(lastUpdate) : '--:--'}`;
  }

  const [history, setHistory] = useState<HistoryPoint[]>([]);
  useEffect(() => {
    const request = new AbortController();
    fetchHistory(request.signal).then(result => {
      if (!request.signal.aborted) setHistory(result.points);
    }).catch(() => { if (!request.signal.aborted) setHistory([]); });
    return () => request.abort();
  }, [lastUpdate]);
  const heart = vitals.find(v => v.id === 'heart-rate');
  const end = Date.parse(history[history.length - 1]?.received_at ?? '');
  const samples = history.filter(p => p.heart_rate !== null && Date.parse(p.received_at) >= end - 120000);
  const values = samples.map(p => p.heart_rate as number);
  const low = Math.min(...values) - 3;
  const range = Math.max(...values) + 3 - low;
  const start = Date.parse(samples[0]?.received_at ?? '');
  const line = samples.map((p, i) => `${(Date.parse(p.received_at)-start)/Math.max(1,end-start)*600},${115-(values[i]-low)/range*110}`).join(' ');

  return (
    <>
      <section className="ungu-heart">
        <div className="flex items-center justify-between gap-2"><h2>Detak jantung · 2 menit</h2><small title={error ?? undefined}>{chip.label}{heart?.simulated && ' · Simulasi'}</small></div>
        <p className="ungu-number">{heart?.value ?? '—'} <span>bpm</span></p>
        <p>{heart?.statusLabel} · {lastUpdate ? formatTimestamp(lastUpdate) : 'Menunggu perangkat'}</p>
        {!usingMockData && samples.length > 1 ? <figure>
          <svg viewBox="0 0 600 120" preserveAspectRatio="none" role="img" aria-label="Tren detak jantung dari pembacaan tersimpan"><polyline points={line} fill="none" stroke="currentColor" strokeWidth="3" vectorEffect="non-scaling-stroke" /></svg>
          <figcaption>{formatTimestamp(samples[0].received_at)} — {formatTimestamp(samples[samples.length-1].received_at)}</figcaption>
        </figure> : <p className="my-6">Menunggu riwayat detak jantung.</p>}
      </section>
      <StatusBanner
        tone={tone}
        title={usingMockData ? 'Mode Data Demo' : connection === 'stale' ? 'Pembacaan tertunda' : BANNER_TITLE[tone]}
        badge={usingMockData ? 'Demo' : connection === 'stale' ? 'Tertunda' : 'Terpantau'}
        message={message}
      />

      <section className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-base font-semibold tracking-tight text-on-surface">
            Tanda vital
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
