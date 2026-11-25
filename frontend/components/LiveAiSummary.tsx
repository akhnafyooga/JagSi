'use client';

import { useAiSummary } from '@/lib/useAiSummary';

import { AiHealthSummary } from './AiHealthSummary';

/** Shows the team-trained model's latest observation window. */
export function LiveAiSummary() {
  const summary = useAiSummary();
  return (
    <AiHealthSummary
      text={summary.text}
      model={summary.badge}
      updatedAt={summary.updatedAt}
      loading={summary.loading}
      simulated={summary.simulated}
      onRefresh={summary.refresh}
    />
  );
}
