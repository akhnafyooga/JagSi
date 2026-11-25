import { TopAppBar } from '@/components/TopAppBar';
import { LiveVitals } from '@/components/LiveVitals';
import { LiveFallStatus } from '@/components/LiveFallStatus';
import { elder } from '@/lib/mock-data';

export default function MonitoringPage() {
  return (
    <>
      <TopAppBar title="Monitoring" subtitle={elder.name} />
      <div className="jagsi-panels">
        <div className="space-y-4"><LiveVitals /></div>
        <LiveFallStatus />
      </div>
    </>
  );
}
