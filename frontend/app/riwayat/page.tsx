'use client';

import { useEffect, useState } from 'react';
import { TopAppBar } from '@/components/TopAppBar';
import { TrendChart } from '@/components/TrendChart';
import { DEVICE_ID, fetchHistory, formatTimestamp, type HistoryPoint } from '@/lib/api';


const metrics = [
  { field: 'heart_rate', label: 'Detak jantung', unit: 'bpm', color: '#bc9eff' },
  { field: 'spo2', label: 'Saturasi oksigen', unit: '%', color: '#0369a1' },
  { field: 'body_temperature', label: 'Suhu tubuh', unit: '°C', color: '#7c3aed' },
] as const;

export default function RiwayatPage() {
  const [points, setPoints] = useState<HistoryPoint[]>();
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const request = new AbortController();
    fetchHistory(request.signal).then(({ points }) => {
      if (!request.signal.aborted) {
        setPoints([...points].sort((a, b) => Date.parse(a.received_at) - Date.parse(b.received_at)));
      }
    }).catch(() => {
      if (!request.signal.aborted) setFailed(true);
    });
    return () => request.abort();
  }, [attempt]);

  function refresh() {
    setPoints(undefined);
    setFailed(false);
    setAttempt((previous) => previous + 1);
  }

  return (
    <>
      <TopAppBar title="Riwayat kesehatan" subtitle="Jendela pembacaan tersimpan" />
      <div className="ungu-dashboard">
        <section className="ungu-panel ungu-history-tools md:col-span-full">
          <h2>Rentang pembacaan</h2>
          <p className="text-sm">Perangkat {DEVICE_ID} · Maksimal 60 pembacaan terakhir</p>
          <button type="button" onClick={refresh} className="ungu-action">
            {failed ? 'Coba lagi' : 'Perbarui riwayat'}
          </button>
          <p role="status" className="empty:hidden">
            {failed ? 'Riwayat tidak tersedia.' : !points ? 'Memuat riwayat…' : points.length === 0 ? 'Belum ada pembacaan.' : ''}
          </p>
        </section>
        {points && points.length > 0 && metrics.map(({ field, label, unit, color }) => {
          const samples = points.flatMap((point) => {
            const value = point[field];
            return typeof value === 'number' && Number.isFinite(value)
              ? [{ value, time: point.received_at }] : [];
          });
          const chart = samples.map((sample, index) => ({
            value: sample.value,
            label: index === 0 || index === samples.length - 1 ? formatTimestamp(sample.time) : '',
          }));
          const missing = points.length - samples.length;
          return (
            <section key={field} className={field === "heart_rate" ? "ungu-heart" : "ungu-panel"} aria-label={label}>
              <h2 className="font-semibold">{label}</h2>
              {samples.length > 0 ? (
                <p className="text-sm">Rata-rata {(samples.reduce((sum, point) => sum + point.value, 0) / samples.length).toFixed(1)} {unit}</p>
              ) : <p className="text-sm">Belum ada nilai.</p>}
              {missing > 0 ? (
                <p className="text-sm">Grafik tidak tersedia karena {missing} pembacaan kosong.</p>
              ) : <TrendChart data={chart} unit={unit} color={color} />}
            </section>
          );
        })}
      </div>
    </>
  );
}
