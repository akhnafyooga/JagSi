import { describe, expect, it } from 'vitest';

import {
  type ApiAlert,
  type ApiVital,
  formatTimestamp,
  overallTone,
  toAlertItem,
  toVital,
} from '../api';

function apiVital(over: Partial<ApiVital> = {}): ApiVital {
  return {
    id: 'temperature',
    label: 'Suhu Tubuh',
    value: 36.6,
    unit: '°C',
    icon: 'thermostat',
    tone: 'normal',
    statusLabel: 'Normal',
    note: 'Acuan 36.1-37.5°C',
    reference: 'Acuan 36.1-37.5°C',
    simulated: false,
    ...over,
  };
}

describe('toVital', () => {
  it('carries value, tone and the simulated flag through', () => {
    const vital = toVital(apiVital());
    expect(vital.value).toBe(36.6);
    expect(vital.tone).toBe('normal');
    expect(vital.simulated).toBe(false);
  });

  it('flags a potentiometer reading as simulated', () => {
    const vital = toVital(apiVital({ id: 'heart-rate', simulated: true }));
    expect(vital.simulated).toBe(true);
  });

  it('maps an absent reading to warning with a null value, never to normal', () => {
    const vital = toVital(apiVital({ value: null, tone: 'unknown', statusLabel: 'Tidak Ada Data' }));
    expect(vital.value).toBeNull();
    expect(vital.tone).toBe('warning');
  });
});

describe('overallTone', () => {
  it('is normal when every card is normal', () => {
    expect(overallTone([toVital(apiVital()), toVital(apiVital())])).toBe('normal');
  });

  it('reports the worst tone present', () => {
    const vitals = [
      toVital(apiVital()),
      toVital(apiVital({ tone: 'warning' })),
      toVital(apiVital({ tone: 'critical' })),
    ];
    expect(overallTone(vitals)).toBe('critical');
  });

  it('prefers warning over normal', () => {
    expect(overallTone([toVital(apiVital()), toVital(apiVital({ tone: 'warning' }))])).toBe(
      'warning',
    );
  });
});

function apiAlert(over: Partial<ApiAlert> = {}): ApiAlert {
  return {
    alert_id: 'ml-1',
    device_id: 'jagsi-watch-01',
    alert_type: 'fall_detected',
    source: 'ml',
    status: 'unresolved',
    timestamp: '2026-11-04T12:00:05Z',
    received_at: '2026-11-04T12:00:05Z',
    confidence: 0.94,
    accel_peak_g: 2.8,
    attempts: 1,
    vitals: null,
    ...over,
  };
}

describe('toAlertItem', () => {
  it('labels a model alert and shows its confidence as a percentage', () => {
    const item = toAlertItem(apiAlert());
    expect(item.title).toBe('Terdeteksi Jatuh');
    expect(item.description).toBe('Model AI (keyakinan 94%)');
    expect(item.tone).toBe('critical');
  });

  it('labels a device-rule alert and omits confidence when there is none', () => {
    const item = toAlertItem(apiAlert({ source: 'device_rule', confidence: null }));
    expect(item.description).toBe('Deteksi perangkat');
  });

  it('shows an acknowledged alert as informational, not critical', () => {
    expect(toAlertItem(apiAlert({ status: 'acknowledged' })).tone).toBe('info');
  });

  it('uses the SOS icon for a manual alert', () => {
    expect(toAlertItem(apiAlert({ alert_type: 'manual_sos' })).icon).toBe('sos');
  });
});

describe('formatTimestamp', () => {
  it('returns a placeholder instead of "Invalid Date"', () => {
    expect(formatTimestamp('not-a-date')).toBe('--:--');
  });

  it('formats a valid ISO timestamp', () => {
    expect(formatTimestamp('2026-11-04T12:00:05Z')).toMatch(/\d{2}[.:]\d{2}/);
  });
});
