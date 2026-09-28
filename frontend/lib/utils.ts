import type { VitalTone } from './types';

export function cn(...classes: Array<string | false | null | undefined>): string {
  return classes.filter(Boolean).join(' ');
}

/**
 * Classify a heart rate (bpm) into a display tone.
 * Reference ranges are intentionally conservative for elderly monitoring.
 */
export function classifyHeartRate(bpm: number): VitalTone {
  if (bpm < 50 || bpm > 120) return 'critical';
  if (bpm < 60 || bpm > 100) return 'warning';
  return 'normal';
}

export function classifySpO2(value: number): VitalTone {
  if (value < 90) return 'critical';
  if (value < 95) return 'warning';
  return 'normal';
}

export function classifyTemperature(celsius: number): VitalTone {
  if (celsius < 35 || celsius > 39) return 'critical';
  if (celsius < 35.5 || celsius > 37.5) return 'warning';
  return 'normal';
}

export function formatClock(date: Date): string {
  return date.toLocaleTimeString('id-ID', {
    hour: '2-digit',
    minute: '2-digit',
  });
}
