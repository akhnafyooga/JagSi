import type { AlertItem, Vital, VitalTone } from './types';

/**
 * Backend base URL. Set NEXT_PUBLIC_JAGSI_API in .env.local to point the
 * dashboard at a deployed backend; the default matches `uvicorn --port 8000`.
 */
export const API_BASE =
  process.env.NEXT_PUBLIC_JAGSI_API?.replace(/\/$/, '') ?? 'http://localhost:8000';

export const DEVICE_ID = process.env.NEXT_PUBLIC_JAGSI_DEVICE_ID ?? 'jagsi-watch-01';

/** A vital as the backend sends it. `value` is null when the sensor had no reading. */
export interface ApiVital {
  id: string;
  label: string;
  value: number | null;
  unit: string;
  icon: string;
  tone: VitalTone | 'unknown';
  statusLabel: string;
  note: string;
  reference: string;
  simulated: boolean;
}

export interface ApiTelemetry {
  device_id: string;
  received_at: string;
  timestamp: string;
  ts_source: 'device' | 'server';
  simulated: boolean;
  device_state: string | null;
  vitals: ApiVital[];
}

export interface ApiAlert {
  alert_id: string;
  device_id: string;
  alert_type: 'fall_detected' | 'manual_sos';
  source: 'device_rule' | 'ml';
  status: 'unresolved' | 'acknowledged';
  timestamp: string;
  received_at: string;
  confidence: number | null;
  accel_peak_g: number | null;
  attempts: number;
  vitals: Record<string, number | null> | null;
}

/**
 * The backend can report tone 'unknown' when a sensor returned nothing. The UI
 * only knows three tones, so an absent reading is shown as a warning with a
 * null value rather than a reassuring green zero.
 */
export function toVital(api: ApiVital): Vital {
  const tone: VitalTone = api.tone === 'unknown' ? 'warning' : api.tone;
  return {
    id: api.id,
    label: api.label,
    value: api.value,
    unit: api.unit,
    icon: api.icon,
    tone,
    statusLabel: api.statusLabel,
    note: api.note,
    simulated: api.simulated,
  };
}

/** Worst tone across all cards, for the banner at the top of the dashboard. */
export function overallTone(vitals: Vital[]): VitalTone {
  if (vitals.some((v) => v.tone === 'critical')) return 'critical';
  if (vitals.some((v) => v.tone === 'warning')) return 'warning';
  return 'normal';
}

const ALERT_LABEL: Record<ApiAlert['alert_type'], string> = {
  fall_detected: 'Terdeteksi Jatuh',
  manual_sos: 'Tombol SOS Ditekan',
};

const SOURCE_LABEL: Record<ApiAlert['source'], string> = {
  device_rule: 'Deteksi perangkat',
  ml: 'Model AI',
};

export function toAlertItem(alert: ApiAlert): AlertItem {
  const confidence =
    alert.confidence === null ? '' : ` (keyakinan ${Math.round(alert.confidence * 100)}%)`;
  return {
    id: alert.alert_id,
    title: ALERT_LABEL[alert.alert_type] ?? alert.alert_type,
    description: `${SOURCE_LABEL[alert.source] ?? alert.source}${confidence}`,
    time: formatTimestamp(alert.received_at),
    tone: alert.status === 'acknowledged' ? 'info' : 'critical',
    icon: alert.alert_type === 'manual_sos' ? 'sos' : 'personal_injury',
  };
}

/** Renders an ISO-8601 Z timestamp as a local clock time, or '--:--' if unparseable. */
export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '--:--';
  return date.toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit' });
}

async function getJson<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    signal,
    cache: 'no-store',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`);
  }
  return (await response.json()) as T;
}

export function fetchLatestTelemetry(signal?: AbortSignal): Promise<ApiTelemetry> {
  return getJson<ApiTelemetry>(`/api/devices/${DEVICE_ID}/telemetry/latest`, signal);
}

export function fetchAlerts(limit = 10, signal?: AbortSignal): Promise<{ alerts: ApiAlert[] }> {
  return getJson<{ alerts: ApiAlert[] }>(`/api/alerts?limit=${limit}`, signal);
}

export const STREAM_URL = `${API_BASE}/api/stream`;
