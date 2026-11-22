import { TopAppBar } from '@/components/TopAppBar';
import { LiveVitals } from '@/components/LiveVitals';
import { LiveFallStatus } from '@/components/LiveFallStatus';
import { AlertSettingsCard } from '@/components/AlertSettingsCard';
import { LiveAiSummary } from '@/components/LiveAiSummary';
import { ChatAssistant } from '@/components/ChatAssistant';
import { elder } from '@/lib/mock-data';

export default function HomePage() {
  return (
    <>
      <TopAppBar title="JagSi (Jaga Lansia)" subtitle={elder.name} online />

      <main className="space-y-4 px-4 pt-3">
        {/*
          Vital signs and the status banner are live from the backend as of
          Week 6; the AI summary and chat are live as of Week 7 (issue #10);
          the fall status card follows the alert WebSocket as of Week 8 (#13).
        */}
        <AlertSettingsCard compact />

        <LiveVitals />

        <LiveFallStatus />

        <LiveAiSummary />

        <ChatAssistant />
      </main>
    </>
  );
}
