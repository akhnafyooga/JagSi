import { TopAppBar } from '@/components/TopAppBar';
import { Icon } from '@/components/Icon';
import { AlertSettingsCard } from '@/components/AlertSettingsCard';
import { LiveAlertLog } from '@/components/LiveAlertLog';
import { LiveFallStatus } from '@/components/LiveFallStatus';

export default function DaruratPage() {
  return (
    <>
      <TopAppBar title="Pusat darurat" subtitle="Status SOS dan riwayat kejadian" />

      <div className="ungu-dashboard">
        <LiveFallStatus emergency />
        <div className="ungu-stack">
        <section className="ungu-panel">
          <a
            href="tel:119"
            className="ungu-action text-error"
            aria-label="Panggil darurat"
          >
            <Icon name="sos" filled className="text-[20px]" />
          </a>
          <h2 className="mt-3 text-base font-semibold text-on-surface">Panggilan Darurat</h2>
          <p className="mt-1 text-xs text-on-surface-variant">
            Buka aplikasi telepon untuk menghubungi layanan darurat.
          </p>
        </section>

        <AlertSettingsCard />

        {/* Live from the backend since Week 8 (issue #13); was mock data. */}
        <LiveAlertLog />
        </div>
      </div>
    </>
  );
}
