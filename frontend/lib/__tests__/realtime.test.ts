import { describe, expect, it } from 'vitest';

import { makeAlert } from '@/test/fakeSocket';

import {
  alertSocketUrl,
  applyAlertMessage,
  describeAlert,
  parseServerMessage,
  reconnectDelay,
} from '../realtime';

describe('alertSocketUrl', () => {
  it('follows the API base, including TLS', () => {
    expect(alertSocketUrl('http://localhost:8000')).toBe('ws://localhost:8000/ws/alerts');
    expect(alertSocketUrl('https://jagsi.example.com/')).toBe('wss://jagsi.example.com/ws/alerts');
  });
});

describe('applyAlertMessage', () => {
  const older = makeAlert({ alert_id: 'old', received_at: '2026-11-17T12:00:00Z' });
  const newer = makeAlert({ alert_id: 'new', received_at: '2026-11-17T13:00:00Z' });

  it('replaces the list with the hello snapshot, newest first, open alerts only', () => {
    const handled = makeAlert({ alert_id: 'done', status: 'acknowledged' });
    const next = applyAlertMessage([makeAlert({ alert_id: 'stale' })], {
      type: 'hello',
      data: { at: 'x', open_alerts: [older, handled, newer] },
    });
    expect(next.map((a) => a.alert_id)).toEqual(['new', 'old']);
  });

  it('adds a new alert once, even if it is pushed twice', () => {
    const once = applyAlertMessage([older], { type: 'alert', data: newer });
    expect(once.map((a) => a.alert_id)).toEqual(['new', 'old']);
    expect(applyAlertMessage(once, { type: 'alert', data: newer })).toBe(once);
  });

  it('ignores an alert that is already handled or empty', () => {
    const list = [older];
    expect(applyAlertMessage(list, { type: 'alert', data: makeAlert({ status: 'acknowledged' }) })).toBe(list);
    expect(applyAlertMessage(list, { type: 'alert', data: null })).toBe(list);
  });

  it('removes an alert when anyone acknowledges it', () => {
    expect(applyAlertMessage([newer, older], { type: 'alert_ack', data: { alert_id: 'new' } })).toEqual([older]);
    expect(
      applyAlertMessage([older], {
        type: 'ack_result',
        data: { alert_id: 'old', status: 'acknowledged', already_acknowledged: false },
      }),
    ).toEqual([]);
  });

  it('leaves the list alone for pings', () => {
    const list = [older];
    expect(applyAlertMessage(list, { type: 'ping' })).toBe(list);
  });
});

describe('parseServerMessage', () => {
  it('rejects anything that is not a typed JSON object', () => {
    expect(parseServerMessage('not json')).toBeNull();
    expect(parseServerMessage('{"no":"type"}')).toBeNull();
    expect(parseServerMessage(new ArrayBuffer(2))).toBeNull();
    expect(parseServerMessage('{"type":"pong"}')).toEqual({ type: 'pong' });
  });
});

describe('reconnectDelay', () => {
  it('backs off exponentially and caps at 30 seconds', () => {
    expect([0, 1, 2, 3].map(reconnectDelay)).toEqual([1000, 2000, 4000, 8000]);
    expect(reconnectDelay(10)).toBe(30_000);
  });
});

describe('describeAlert', () => {
  it('words SOS, device falls and ML falls differently', () => {
    expect(describeAlert(makeAlert({ alert_type: 'manual_sos' }), 'Ibu Sari').title).toBe(
      'Ibu Sari menekan tombol SOS',
    );
    expect(describeAlert(makeAlert(), 'Ibu Sari').body).toContain('Sensor gerak');
    expect(describeAlert(makeAlert({ source: 'ml', confidence: 0.873 }), 'Ibu Sari').body).toContain(
      'keyakinan 87%',
    );
  });
});
