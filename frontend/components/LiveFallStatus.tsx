'use client';

import { formatTimestamp } from '@/lib/api';

import { useEmergencyAlertContext } from './EmergencyAlertsProvider';
import { FallStatusCard } from './FallStatusCard';

/**
 * The fall card on the home page, driven by the alert WebSocket (issue #13).
 * Until Week 8 it always said "Aman" because it read the mock data.
 */
export function LiveFallStatus() {
  const ctx = useEmergencyAlertContext();
  const open = ctx?.open ?? [];
  const latest = open[0];

  if (!ctx || ctx.connection === 'unsupported') {
    return <FallStatusCard tone="unknown" status="Tidak diketahui" label="Status Gerak / Jatuh" note="Browser tidak mendukung peringatan langsung" />;
  }
  if (latest) {
    const sos = latest.alert_type === 'manual_sos';
    return (
      <FallStatusCard
        tone="critical"
        status={sos ? 'SOS Ditekan' : 'Terdeteksi Jatuh'}
        label="Status Gerak / Jatuh"
        note={`Belum ditangani · ${formatTimestamp(latest.received_at)}`}
      />
    );
  }
  if (ctx.connection !== 'live') {
    return <FallStatusCard tone="unknown" status="Menunggu koneksi" label="Status Gerak / Jatuh" note="Peringatan langsung belum tersambung" />;
  }
  return <FallStatusCard tone="normal" status="Aman" label="Status Gerak / Jatuh" note="Tidak ada peringatan terbuka" />;
}
