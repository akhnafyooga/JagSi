'use client';

import { useEffect, useRef, useState } from 'react';

import {
  type ApiAlert,
  type ApiTelemetry,
  STREAM_URL,
  fetchAlerts,
  fetchLatestTelemetry,
  toAlertItem,
  toVital,
} from './api';
import { alerts as mockAlerts, vitals as mockVitals } from './mock-data';
import type { AlertItem, Vital } from './types';

export type ConnectionState =
  | 'connecting'
  /** Server-sent events are open; cards update as the device publishes. */
  | 'live'
  /** The backend answered once but the stream is down; values may be stale. */
  | 'stale'
  /** The backend is unreachable; the cards below are the demo data. */
  | 'offline';

export interface LiveVitals {
  connection: ConnectionState;
  vitals: Vital[];
  alerts: AlertItem[];
  /** True while the shown numbers are mock data, not anything a device sent. */
  usingMockData: boolean;
  lastUpdate: string | null;
  deviceState: string | null;
  error: string | null;
}

const REFRESH_MS = 5000;

/**
 * Subscribes the dashboard to live telemetry.
 *
 * Three sources, in order of preference:
 *   1. Server-sent events from /api/stream, pushed as the device publishes.
 *   2. Polling /api/telemetry/latest, if the stream cannot be opened.
 *   3. The mock data from issue #12, if the backend is not running at all.
 *
 * The third case is kept deliberately, because a dashboard that renders nothing
 * when the backend is down is harder to develop against. It is always reported
 * through `usingMockData` so the UI can say so instead of pretending the numbers
 * are real.
 */
export function useLiveVitals(): LiveVitals {
  const [state, setState] = useState<LiveVitals>({
    connection: 'connecting',
    vitals: mockVitals,
    alerts: mockAlerts,
    usingMockData: true,
    lastUpdate: null,
    deviceState: null,
    error: null,
  });

  // Held in a ref so the polling fallback does not re-subscribe on every render.
  const everConnected = useRef(false);

  useEffect(() => {
    const controller = new AbortController();
    let stream: EventSource | null = null;
    let poll: ReturnType<typeof setInterval> | null = null;
    let cancelled = false;

    const applyTelemetry = (payload: ApiTelemetry, connection: ConnectionState) => {
      if (cancelled) return;
      everConnected.current = true;
      setState((prev) => ({
        ...prev,
        connection,
        vitals: payload.vitals.map(toVital),
        usingMockData: false,
        lastUpdate: payload.received_at,
        deviceState: payload.device_state,
        error: null,
      }));
    };

    const applyAlerts = (incoming: ApiAlert[]) => {
      if (cancelled) return;
      setState((prev) => ({ ...prev, alerts: incoming.map(toAlertItem) }));
    };

    const markUnreachable = (message: string) => {
      if (cancelled) return;
      setState((prev) => ({
        ...prev,
        // Keep whatever real data we already have rather than reverting to mock.
        connection: everConnected.current ? 'stale' : 'offline',
        usingMockData: everConnected.current ? prev.usingMockData : true,
        vitals: everConnected.current ? prev.vitals : mockVitals,
        alerts: everConnected.current ? prev.alerts : mockAlerts,
        error: message,
      }));
    };

    const loadOnce = async () => {
      try {
        const telemetry = await fetchLatestTelemetry(controller.signal);
        applyTelemetry(telemetry, stream ? 'live' : 'stale');
      } catch (error) {
        if (controller.signal.aborted) return;
        markUnreachable(error instanceof Error ? error.message : 'backend unreachable');
        return;
      }
      try {
        const { alerts: incoming } = await fetchAlerts(10, controller.signal);
        applyAlerts(incoming);
      } catch {
        // Alerts are secondary; a failure here must not blank the vitals.
      }
    };

    void loadOnce();

    if (typeof EventSource !== 'undefined') {
      stream = new EventSource(STREAM_URL);

      // The event payload carries the row, but re-reading the endpoint keeps one
      // shaping path (the backend's) instead of two that can drift apart.
      stream.addEventListener('telemetry', () => void loadOnce());
      stream.addEventListener('alert', () => void loadOnce());
      stream.addEventListener('alert_ack', () => void loadOnce());
      stream.addEventListener('status', () => void loadOnce());

      stream.onopen = () => {
        if (cancelled) return;
        setState((prev) => ({
          ...prev,
          connection: prev.usingMockData ? prev.connection : 'live',
          error: null,
        }));
      };

      stream.onerror = () => {
        // EventSource retries on its own, so this is not fatal. Fall back to
        // polling so the cards keep moving in the meantime.
        markUnreachable('live stream interrupted');
        if (poll === null) poll = setInterval(() => void loadOnce(), REFRESH_MS);
      };
    } else {
      poll = setInterval(() => void loadOnce(), REFRESH_MS);
    }

    return () => {
      cancelled = true;
      controller.abort();
      stream?.close();
      if (poll !== null) clearInterval(poll);
    };
  }, []);

  return state;
}
