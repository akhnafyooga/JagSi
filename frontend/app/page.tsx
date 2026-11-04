import { TopAppBar } from '@/components/TopAppBar';
import { LiveVitals } from '@/components/LiveVitals';
import { FallStatusCard } from '@/components/FallStatusCard';
import { AiHealthSummary } from '@/components/AiHealthSummary';
import { ChatAssistant } from '@/components/ChatAssistant';
import { aiSummary, elder, fallStatus } from '@/lib/mock-data';

export default function HomePage() {
  return (
    <>
      <TopAppBar title="JagSi (Jaga Lansia)" subtitle={elder.name} online />

      <main className="space-y-4 px-4 pt-3">
        {/*
          Vital signs and the status banner are live from the backend as of
          Week 6. The fall status card, AI summary and chat below are still the
          mock data from issue #12: the fall card needs the alert stream wired
          in, and the AI summary needs the Gemini service (Sprint 4).
        */}
        <LiveVitals />

        <FallStatusCard
          status={fallStatus.status}
          label={fallStatus.label}
          note={fallStatus.note}
        />

        <AiHealthSummary
          text={aiSummary.text}
          model={aiSummary.model}
          updatedAt={aiSummary.updatedAt}
        />

        <ChatAssistant />
      </main>
    </>
  );
}
