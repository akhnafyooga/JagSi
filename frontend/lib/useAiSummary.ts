'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

import { type ApiSummary, fetchSummary, formatTimestamp, summarySourceLabel } from './api';
import { aiSummary as mockSummary } from './mock-data';

export interface AiSummaryState {
  text: string;
  badge: string;
  updatedAt: string;
  source: ApiSummary['source'] | 'demo';
  loading: boolean;
  /** True when the reading behind the text is a Wokwi potentiometer. */
  simulated: boolean;
  refresh: () => void;
}

const REFRESH_MS = 5 * 60 * 1000;

/**
 * The AI card's data (issue #10).
 *
 * Asks the backend, which uses Gemini when a key is configured and its own
 * rule-based summary otherwise. Falls back to the issue #12 demo text only when
 * the backend cannot be reached, and labels it as demo data when it does.
 */
export function useAiSummary(): AiSummaryState {
  const [summary, setSummary] = useState<ApiSummary | null>(null);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);
  const controller = useRef<AbortController | null>(null);

  const load = useCallback(async (refresh: boolean) => {
    controller.current?.abort();
    const ctrl = new AbortController();
    controller.current = ctrl;
    setLoading(true);
    try {
      const next = await fetchSummary(refresh, ctrl.signal);
      setSummary(next);
      setFailed(false);
    } catch (err) {
      if ((err as Error).name !== 'AbortError') setFailed(true);
    } finally {
      if (controller.current === ctrl) setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load(false);
    const timer = setInterval(() => void load(false), REFRESH_MS);
    return () => {
      clearInterval(timer);
      controller.current?.abort();
    };
  }, [load]);

  const refresh = useCallback(() => void load(true), [load]);

  if (summary && !failed) {
    return {
      text: summary.text,
      badge: summarySourceLabel(summary.source, summary.model),
      updatedAt: `Diperbarui ${formatTimestamp(summary.generated_at)}`,
      source: summary.source,
      loading,
      simulated: summary.based_on.simulated,
      refresh,
    };
  }
  return {
    text: mockSummary.text,
    badge: summarySourceLabel('demo', ''),
    updatedAt: loading ? 'Memuat…' : 'Server tidak terjangkau',
    source: 'demo',
    loading,
    simulated: false,
    refresh,
  };
}
