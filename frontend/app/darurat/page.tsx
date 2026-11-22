import { TopAppBar } from '@/components/TopAppBar';
import { Icon } from '@/components/Icon';
import { AlertSettingsCard } from '@/components/AlertSettingsCard';
import { LiveAlertLog } from '@/components/LiveAlertLog';
import { elder } from '@/lib/mock-data';

export default function DaruratPage() {
  return (
    <>
      <TopAppBar title="Peringatan & Darurat" subtitle={elder.name} online />

      <main className="space-y-4 px-4 pt-3">
        {/* SOS button */}
        <section className="rounded-2xl border border-error/30 bg-error/5 p-4 text-center">
          <a
            href="tel:119"
            className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-error text-on-error shadow-lg transition-transform active:scale-95"
            aria-label="Panggil darurat"
          >
            <Icon name="sos" filled className="text-[40px]" />
          </a>
          <h2 className="mt-3 text-base font-semibold text-on-surface">Panggilan Darurat</h2>
          <p className="mt-1 text-xs text-on-surface-variant">
            Tekan dan tahan untuk memanggil ambulans / layanan gawat darurat (119).
          </p>
        </section>

        <AlertSettingsCard />

        {/* Live from the backend since Week 8 (issue #13); was mock data. */}
        <LiveAlertLog />
      </main>
    </>
  );
}
