import type { ApiAlert } from '@/lib/api';

/** Minimal stand-in for the browser WebSocket, driven by the test. */
export class FakeSocket {
  static instances: FakeSocket[] = [];
  readyState = 0;
  sent: unknown[] = [];
  onopen: (() => void) | null = null;
  onmessage: ((e: { data: string }) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(public url: string) {
    FakeSocket.instances.push(this);
  }

  static latest(): FakeSocket {
    return FakeSocket.instances[FakeSocket.instances.length - 1];
  }

  static reset() {
    FakeSocket.instances = [];
  }

  open() {
    this.readyState = 1;
    this.onopen?.();
  }

  receive(msg: unknown) {
    this.onmessage?.({ data: JSON.stringify(msg) });
  }

  send(data: string) {
    this.sent.push(JSON.parse(data));
  }

  close() {
    if (this.readyState === 3) return;
    this.readyState = 3;
    this.onclose?.();
  }
}

export const createFakeSocket = (url: string) => new FakeSocket(url) as unknown as WebSocket;

export function makeAlert(overrides: Partial<ApiAlert> = {}): ApiAlert {
  return {
    alert_id: 'a-1',
    device_id: 'jagsi-watch-01',
    alert_type: 'fall_detected',
    source: 'device_rule',
    status: 'unresolved',
    timestamp: '2026-11-17T13:00:00Z',
    received_at: '2026-11-17T13:00:00Z',
    confidence: null,
    accel_peak_g: 3.1,
    attempts: 1,
    vitals: { heart_rate: 112, spo2: 94, body_temperature: 36.9 },
    ...overrides,
  };
}
