import { TopAppBar } from '@/components/TopAppBar';
import { StatusBanner } from '@/components/StatusBanner';
import { VitalCard } from '@/components/VitalCard';
import { FallStatusCard } from '@/components/FallStatusCard';
import { Icon } from '@/components/Icon';
import { elder, fallStatus, vitals } from '@/lib/mock-data';

export default function MonitoringPage() {
  const [heartRate, ...others] = vitals;

  return (
    <>
      <TopAppBar title="Monitoring Lansia" subtitle={elder.name} online />

      <main className="space-y-4 px-4 pt-3">
        <StatusBanner
          tone="normal"
          title="Semua Tanda Vital Normal"
          badge="Live"
          message="Pembaruan waktu nyata setiap 10 detik"
        />

        {/* Hero: primary metric */}
        <section className="rounded-2xl border border-surface-container-highest/60 bg-gradient-to-br from-primary to-primary-dim p-6 text-center text-on-primary shadow-sm">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-white/20">
            <Icon name="favorite" filled className="text-[26px]" />
          </div>
          <p className="text-sm font-medium text-white/80">{heartRate.label}</p>
          <div className="mt-1 flex items-baseline justify-center gap-1">
            <span className="text-6xl font-bold leading-none">{heartRate.value}</span>
            <span className="text-xl">{heartRate.unit}</span>
          </div>
          <p className="mt-2 text-xs text-white/80">Rentang normal 60–100 bpm</p>
        </section>

        <div className="grid grid-cols-2 gap-3">
          {others.map((vital) => (
            <VitalCard key={vital.id} vital={vital} />
          ))}
        </div>

        <FallStatusCard
          status={fallStatus.status}
          label={fallStatus.label}
          note={fallStatus.note}
        />
      </main>
    </>
  );
}
