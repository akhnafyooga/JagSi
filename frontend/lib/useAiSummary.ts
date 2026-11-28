'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { fetchDailyBrief } from './dailyBrief';


export function useAiSummary() {
  const [summary, setSummary] = useState<Awaited<ReturnType<typeof fetchDailyBrief>> | null>(null);
  const [loading, setLoading] = useState(true);
  const [failed, setFailed] = useState(false);
  const request = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    if (request.current) return;
    const controller = new AbortController();
    request.current = controller;
    const timeout = setTimeout(() => controller.abort(), 75000);
    setLoading(true);
    try {
      const next = await fetchDailyBrief(controller.signal);
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
    const timer = setInterval(refresh, 60000);
    return () => {
      clearInterval(timer);
      request.current?.abort();
      request.current = null;
    };
  }, [refresh]);

  return {
    text: summary?.text ?? (failed ? 'Ringkasan harian belum tersedia.' : 'Memuat pembacaan…'),
    badge: summary?.model ?? 'Status pembacaan',
    updatedAt: '',
    simulated: false,
    loading,
    refresh,
  };
}
