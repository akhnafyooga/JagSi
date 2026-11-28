import { API_BASE, type ApiAlert } from './api';

/**
 * Emergency alerts over WebSocket (issue #13).
 *
 * Telemetry still comes over server-sent events (/api/stream). Alerts get their
 * own socket because the caregiver has to answer them: pressing "Saya tangani"
 * sends the acknowledgement back on the same connection, and every other open
 * dashboard closes its emergency screen at the same moment.
 */

/** The backend's /ws/alerts URL, derived from the HTTP base so one env var configures both. */
export function alertSocketUrl(apiBase: string = API_BASE): string {
  const base = apiBase.replace(/\/$/, '');
  if (base.startsWith('https://')) return `wss://${base.slice('https://'.length)}/ws/alerts`;
  if (base.startsWith('http://')) return `ws://${base.slice('http://'.length)}/ws/alerts`;
  return `${base}/ws/alerts`;
}

export type ServerMessage =
  | { type: 'hello'; data: { at: string; open_alerts: ApiAlert[] } }
  | { type: 'alert'; data: ApiAlert | null }
  | { type: 'alert_ack'; data: { alert_id: string; via?: string; acked_at?: string } }
  | { type: 'ack_result'; data: { alert_id: string; status: string; already_acknowledged: boolean } }
  | { type: 'ping' | 'pong'; data?: { at: string } }
  | { type: 'error'; data: { message: string; alert_id?: string } };

export function parseServerMessage(raw: unknown): ServerMessage | null {
  if (typeof raw !== 'string') return null;
  try {
    const msg = JSON.parse(raw) as { type?: unknown };
    return msg && typeof msg.type === 'string' ? (msg as ServerMessage) : null;
  } catch {
    return null;
  }
}

/**
 * Open alerts, newest first, after one server message.
 *
 * Pure so it can be tested without a socket. The hello snapshot replaces the
 * list (a reconnecting dashboard catches up on alerts it missed); an alert that
 * is already acknowledged never opens the emergency screen.
 */
export function applyAlertMessage(open: ApiAlert[], msg: ServerMessage): ApiAlert[] {
  switch (msg.type) {
    case 'hello':
      return sortNewestFirst(msg.data.open_alerts.filter((a) => a.status === 'unresolved'));
    case 'alert': {
      const alert = msg.data;
      if (!alert || alert.status !== 'unresolved') return open;
      if (open.some((a) => a.alert_id === alert.alert_id)) return open;
      return sortNewestFirst([alert, ...open]);
    }
    case 'alert_ack':
    case 'ack_result':
      return removeAlert(open, msg.data.alert_id);
    default:
      return open;
  }
}

export function removeAlert(open: ApiAlert[], alertId: string): ApiAlert[] {
  const next = open.filter((a) => a.alert_id !== alertId);
  return next.length === open.length ? open : next;
}

function sortNewestFirst(alerts: ApiAlert[]): ApiAlert[] {
  return [...alerts].sort((a, b) => b.received_at.localeCompare(a.received_at));
}

/** Reconnect delay: 1 s, 2 s, 4 s ... capped at 30 s, so a backend restart is picked up quickly. */
export function reconnectDelay(attempt: number): number {
  return Math.min(30_000, 1000 * 2 ** Math.max(0, attempt));
}

export interface AlertCopy {
  title: string;
  body: string;
  icon: string;
}

/** What the emergency screen and the browser notification say for one alert. */
export function describeAlert(alert: ApiAlert, elderName: string): AlertCopy {
  const sim = alert.source === 'presentation_simulation';
  if (alert.alert_type === 'manual_sos') {
    if (sim) {
      return {
        title: `Simulasi SOS untuk ${elderName}`,
        body: 'Tombol darurat tidak ditekan. Ini latihan dari panel simulasi presentasi. Segera cek kondisi beliau bila ini kejadian nyata.',
        icon: 'sos',
      };
    }
    return {
      title: `${elderName} menekan tombol SOS`,
      body: 'Tombol darurat di jam tangan ditekan. Segera hubungi atau datangi beliau.',
      icon: 'sos',
    };
  }
  if (sim) {
    return {
      title: `Simulasi jatuh untuk ${elderName}`,
      body: 'Tidak ada benturan yang terdeteksi. Ini latihan dari panel simulasi presentasi.',
      icon: 'personal_injury',
    };
  }
  const how =
    alert.source === 'ml'
      ? `Model AI mendeteksi pola jatuh${
          alert.confidence === null ? '' : ` (keyakinan ${Math.round(alert.confidence * 100)}%)`
        }.`
      : 'Sensor gerak di jam tangan mendeteksi benturan keras.';
  return {
    title: `${elderName} kemungkinan terjatuh`,
    body: `${how} Pastikan kondisi beliau sekarang.`,
    icon: 'personal_injury',
  };
}
