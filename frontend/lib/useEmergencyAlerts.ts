'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { acknowledgeAlert, type ApiAlert } from './api';
import {
  alertSocketUrl,
  applyAlertMessage,
  parseServerMessage,
  reconnectDelay,
  removeAlert,
} from './realtime';

export type AlertConnection =
  | 'connecting'
  /** Socket open: a new alert reaches this screen within a second. */
  | 'live'
  /** Socket dropped; retrying. Alerts that fire meanwhile arrive in the next hello. */
  | 'reconnecting'
  /** No WebSocket support at all (very old browser). */
  | 'unsupported';

export interface EmergencyAlerts {
  connection: AlertConnection;
  /** Alerts nobody has acknowledged yet, newest first. */
  open: ApiAlert[];
  /** Alert ids whose acknowledgement is on its way. */
  pending: string[];
  /** Bumps on every alert or acknowledgement, so lists can refetch their history. */
  revision: number;
  error: string | null;
  acknowledge(alertId: string): Promise<void>;
}

export interface EmergencyAlertOptions {
  /** Called once per alert that is new to this screen (not for the hello snapshot). */
  onNewAlert?: (alert: ApiAlert) => void;
  /** For tests. Defaults to the browser's WebSocket. */
  createSocket?: (url: string) => WebSocket;
  url?: string;
}

const PING_EVERY_MS = 25_000;

export function useEmergencyAlerts(options: EmergencyAlertOptions = {}): EmergencyAlerts {
  const [open, setOpen] = useState<ApiAlert[]>([]);
  const [pending, setPending] = useState<string[]>([]);
  const [connection, setConnection] = useState<AlertConnection>('connecting');
  const [revision, setRevision] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const openRef = useRef<ApiAlert[]>([]);
  // Callbacks in refs so a new onNewAlert identity does not tear the socket down.
  const onNewAlertRef = useRef(options.onNewAlert);
  onNewAlertRef.current = options.onNewAlert;
  const createSocketRef = useRef(options.createSocket);
  const url = options.url ?? alertSocketUrl();

  const commit = useCallback((next: ApiAlert[]) => {
    openRef.current = next;
    setOpen(next);
  }, []);

  useEffect(() => {
    const factory =
      createSocketRef.current ??
      (typeof WebSocket === 'undefined' ? null : (u: string) => new WebSocket(u));
    if (!factory) {
      setConnection('unsupported');
      return;
    }

    let stopped = false;
    let attempt = 0;
    let retry: ReturnType<typeof setTimeout> | null = null;
    let ping: ReturnType<typeof setInterval> | null = null;

    const connect = () => {
      if (stopped) return;
      setConnection(attempt === 0 ? 'connecting' : 'reconnecting');
      let ws: WebSocket;
      try {
        ws = factory(url);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'cannot open alert socket');
        scheduleRetry();
        return;
      }
      socketRef.current = ws;

      ws.onopen = () => {
        attempt = 0;
        setConnection('live');
        setError(null);
        if (ping !== null) clearInterval(ping);
        ping = setInterval(() => {
          if (ws.readyState === 1) ws.send(JSON.stringify({ type: 'ping' }));
        }, PING_EVERY_MS);
      };

      ws.onmessage = (event: MessageEvent) => {
        const msg = parseServerMessage(event.data);
        if (!msg) return;
        if (msg.type === 'error') {
          setError(msg.data.message);
          if (msg.data.alert_id) {
            const id = msg.data.alert_id;
            setPending((p) => p.filter((x) => x !== id));
          }
          return;
        }
        const before = openRef.current;
        const next = applyAlertMessage(before, msg);
        if (msg.type === 'alert' && next !== before && msg.data) {
          onNewAlertRef.current?.(msg.data);
        }
        if (msg.type === 'alert_ack' || msg.type === 'ack_result') {
          const id = msg.data.alert_id;
          setPending((p) => p.filter((x) => x !== id));
        }
        if (msg.type === 'alert' || msg.type === 'alert_ack') setRevision((r) => r + 1);
        if (next !== before) commit(next);
      };

      ws.onclose = () => {
        if (ping !== null) clearInterval(ping);
        ping = null;
        if (socketRef.current === ws) socketRef.current = null;
        if (!stopped) scheduleRetry();
      };

      ws.onerror = () => {
        setError('koneksi peringatan terputus');
      };
    };

    const scheduleRetry = () => {
      if (stopped) return;
      setConnection('reconnecting');
      const delay = reconnectDelay(attempt);
      attempt += 1;
      retry = setTimeout(connect, delay);
    };

    connect();

    return () => {
      stopped = true;
      if (retry !== null) clearTimeout(retry);
      if (ping !== null) clearInterval(ping);
      const ws = socketRef.current;
      socketRef.current = null;
      ws?.close();
    };
  }, [url, commit]);

  const acknowledge = useCallback(
    async (alertId: string) => {
      setPending((p) => (p.includes(alertId) ? p : [...p, alertId]));
      const ws = socketRef.current;
      if (ws && ws.readyState === 1) {
        // The answer (ack_result to us, alert_ack to everyone) removes it.
        ws.send(JSON.stringify({ type: 'ack', alert_id: alertId }));
        return;
      }
      // Socket down: the REST endpoint does the same work on the backend.
      try {
        await acknowledgeAlert(alertId);
        commit(removeAlert(openRef.current, alertId));
        setRevision((r) => r + 1);
        setError(null);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'gagal mengonfirmasi peringatan');
      } finally {
        setPending((p) => p.filter((x) => x !== alertId));
      }
    },
    [commit],
  );

  return { connection, open, pending, revision, error, acknowledge };
}
