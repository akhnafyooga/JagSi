import { TopAppBar } from '@/components/TopAppBar';
import { StatusBanner } from '@/components/StatusBanner';
import { VitalCard } from '@/components/VitalCard';
import { FallStatusCard } from '@/components/FallStatusCard';
import { AiHealthSummary } from '@/components/AiHealthSummary';
import { ChatAssistant } from '@/components/ChatAssistant';
import { aiSummary, elder, fallStatus, vitals } from '@/lib/mock-data';

export default function HomePage() {
  return (
    <>
      <TopAppBar title="JagSi (Jaga Lansia)" subtitle={elder.name} online />

      <main className="space-y-4 px-4 pt-3">
        <StatusBanner
          tone="normal"
          title="Semua Tanda Vital Normal"
          badge="Terpantau"
          message="Data terakhir diperbarui 5 menit lalu"
        />

        <section className="space-y-2">
          <h2 className="text-base font-semibold tracking-tight text-on-surface">
            Live Vital Signs
          </h2>
          <div className="grid grid-cols-2 gap-3">
            {vitals.map((vital) => (
              <VitalCard key={vital.id} vital={vital} />
            ))}
          </div>
        </section>

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
