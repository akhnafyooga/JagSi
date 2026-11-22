'use client';

import { useAiSummary } from '@/lib/useAiSummary';

import { AiHealthSummary } from './AiHealthSummary';

/** The AI card wired to /api/devices/{id}/summary (issue #10). */
export function LiveAiSummary() {
  const summary = useAiSummary();
  return (
    <AiHealthSummary
      text={summary.text}
      model={summary.badge}
      updatedAt={summary.updatedAt}
      loading={summary.loading}
      // The rule-based text already says so; only add the note when it does not.
      simulated={summary.simulated && !summary.text.toLowerCase().includes('simulasi')}
      onRefresh={summary.refresh}
    />
  );
}
