'use client';

import { TopAppBar } from '@/components/TopAppBar';
import { LiveVitals } from '@/components/LiveVitals';
import { LiveFallStatus } from '@/components/LiveFallStatus';
import { AlertSettingsCard } from '@/components/AlertSettingsCard';
import { LiveAiSummary } from '@/components/LiveAiSummary';
import { ChatAssistant } from '@/components/ChatAssistant';
import { elder } from '@/lib/mock-data';
import { useCaregiverProfile } from '@/lib/useCaregiverProfile';

export default function HomePage() {
  const { wearerName } = useCaregiverProfile();
  return (
    <>
      <TopAppBar title="Ringkasan hari ini" subtitle={wearerName ?? elder.name} />

      <div className="ungu-dashboard">
        <div className="min-w-0"><LiveVitals /></div>
        <aside className="ungu-stack">
          <LiveAiSummary />
          <ChatAssistant />
          <LiveFallStatus />
          <AlertSettingsCard compact />
        </aside>
      </div>
    </>
  );
}

