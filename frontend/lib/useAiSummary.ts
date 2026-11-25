'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchProgress, formatTimestamp } from './api';
import { trendSummary } from './trendSummary';

export function useAiSummary() {
  const [summary, setSummary] = useState<ReturnType<typeof trendSummary> | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const request = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    const timeout = setTimeout(() => controller.abort(), 8000);
    setLoading(true);
    try {
      const next = trendSummary(await fetchProgress(controller.signal));
      if (request.current === controller) {
        setSummary(next);
        setFailed(false);
      }
    } catch {
      if (request.current === controller) {
        setSummary(null);
        setFailed(true);
      }
    } finally {
      clearTimeout(timeout);
      if (request.current === controller) {
        request.current = null;
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = setInterval(refresh, 5000);
    return () => {
      clearInterval(timer);
      request.current?.abort();
      request.current = null;
    };
  }, [refresh]);

  return {
    text: summary?.text ?? (failed ? 'Ringkasan tren tidak tersedia.' : 'Memuat pembacaan…'),
    badge: summary?.badge ?? 'Status pembacaan',
    updatedAt: summary?.observedAt ? `Pembacaan terakhir ${formatTimestamp(summary.observedAt)}` : '',
    simulated: summary?.simulated ?? false,
    loading,
    refresh,
  };
}
