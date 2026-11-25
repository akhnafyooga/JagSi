import { describe, expect, it } from 'vitest';
import { trendSummary, type Progress } from '../trendSummary';

const reading = {
  state: 'ready', simulated: true, label: 'rising_hr', model_version: 'v1',
  to: '2026-11-25T09:00:00Z', span_seconds: 118,
  stats: {
    first_10_mean: { heart_rate: 78, spo2: 98, body_temperature: 36.5 },
    last_10_mean: { heart_rate: 94, spo2: 98, body_temperature: 36.5 },
  },
} satisfies Progress;

describe('owned model summary', () => {
  it('uses the observed means and model revision', () => {
    const summary = trendSummary(reading);
    expect(summary.text).toContain('78 bpm');
    expect(summary.text).toContain('94 bpm');
    expect(summary.badge).toContain('v1');
    expect(summary.observedAt).toBe(reading.to);
  });

  it('suppresses trend claims on uncertain or stale input', () => {
    expect(trendSummary({ ...reading, state: 'uncertain' }).text).not.toContain('meningkat');
    expect(trendSummary({ simulated: true, state: 'stale' }).text).toContain('kedaluwarsa');
  });
});
