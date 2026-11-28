import { API_BASE, DEVICE_ID } from './api';

export const reviewedMcuKey = 'jagsi-reviewed-mcu:' + DEVICE_ID;

export async function fetchDailyBrief(signal: AbortSignal) {
  // The onboarding preview is single-device and keeps reviewed labs in this tab.
  const saved = sessionStorage.getItem(reviewedMcuKey);
  const response = await fetch(API_BASE + '/api/devices/' + encodeURIComponent(DEVICE_ID) + '/daily-brief', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: saved || '{}', signal, cache: 'no-store',
  });
  if (!response.ok) throw new Error('Ringkasan belum tersedia.');
  return await response.json() as { text: string; model: string; source: 'rules' | 'local_llm' };
}
