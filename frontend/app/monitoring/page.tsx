import { TopAppBar } from '@/components/TopAppBar';
import { LiveVitals } from '@/components/LiveVitals';
import { LiveFallStatus } from '@/components/LiveFallStatus';

export default function MonitoringPage() {
  return (
    <>
      <TopAppBar title="Monitoring" subtitle="Pembacaan sensor · JagSi Watch 01" />
      <div className="ungu-dashboard monitoring-layout">
        <LiveVitals />
        <LiveFallStatus />
      </div>
    </>
  );
}
