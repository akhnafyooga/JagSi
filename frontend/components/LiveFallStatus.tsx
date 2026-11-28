'use client';

import { formatTimestamp } from '@/lib/api';

import { useEmergencyAlertContext } from './EmergencyAlertsProvider';
import { FallStatusCard } from './FallStatusCard';

/**
 * The fall card on the home page, driven by the alert WebSocket (issue #13).
 * Until Week 8 it always said "Aman" because it read the mock data.
 */
export function LiveFallStatus({ emergency = false }: { emergency?: boolean }) {
  const ctx = useEmergencyAlertContext();
  const open = ctx?.open ?? [];
  const latest = open[0];

  if (!ctx || ctx.connection === 'unsupported') {
    return <FallStatusCard emergency={emergency} tone="unknown" status="Tidak diketahui" label="Status Gerak / Jatuh" note="Browser tidak mendukung peringatan langsung" />;
  }
  if (latest) {
    const sos = latest.alert_type === 'manual_sos';
    const sim = latest.source === 'presentation_simulation';
    return (
      <FallStatusCard
        emergency={emergency}
        tone="critical"
        status={sos ? (sim ? 'Simulasi SOS' : 'SOS Ditekan') : (sim ? 'Simulasi Jatuh' : 'Terdeteksi Jatuh')}
        label="Status Gerak / Jatuh"
        note={`${sim ? 'Latihan presentasi · ' : ''}Belum ditangani · ${formatTimestamp(latest.received_at)}`}
      />
    );
  }
  if (ctx.connection !== 'live') {
    return <FallStatusCard emergency={emergency} tone="unknown" status="Menunggu koneksi" label="Status Gerak / Jatuh" note="Peringatan langsung belum tersambung" />;
  }
  return <FallStatusCard emergency={emergency} tone="normal" status={emergency ? "Tidak ada SOS aktif" : "Aman"} label="Status Gerak / Jatuh" note="Tidak ada peringatan terbuka" />;
}
