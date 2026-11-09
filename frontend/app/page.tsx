import { TopAppBar } from '@/components/TopAppBar';
import { LiveVitals } from '@/components/LiveVitals';
import { FallStatusCard } from '@/components/FallStatusCard';
import { LiveAiSummary } from '@/components/LiveAiSummary';
import { ChatAssistant } from '@/components/ChatAssistant';
import { elder, fallStatus } from '@/lib/mock-data';

export default function HomePage() {
  return (
    <>
      <TopAppBar title="JagSi (Jaga Lansia)" subtitle={elder.name} online />

      <main className="space-y-4 px-4 pt-3">
        {/*
          Vital signs and the status banner are live from the backend as of
          Week 6; the AI summary and chat are live as of Week 7 (issue #10).
          The fall status card is still the mock data from issue #12 until the
          alert stream is wired into it.
        */}
        <LiveVitals />

        <FallStatusCard
          status={fallStatus.status}
          label={fallStatus.label}
          note={fallStatus.note}
        />

        <LiveAiSummary />

        <ChatAssistant />
      </main>
    </>
  );
}
