import { TopAppBar } from '@/components/TopAppBar';
import { StatusBanner } from '@/components/StatusBanner';
import { TrendChart } from '@/components/TrendChart';
import { Icon } from '@/components/Icon';
import { elder, heartRateTrend, spo2Trend, stepsTrend } from '@/lib/mock-data';

export default function RiwayatPage() {
  return (
    <>
      <TopAppBar title="Riwayat Kesehatan" subtitle={elder.name} online />

      <main className="space-y-5 px-4 pt-3">
        <StatusBanner
          tone="normal"
          title="Kondisi Mingguan: Sangat Baik"
          badge="7 hari"
          message="Tidak ada anomali signifikan dalam seminggu terakhir"
        />

        <section className="rounded-2xl border border-surface-container-highest/60 bg-surface-container-lowest p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-on-surface">
              <Icon name="favorite" className="text-[18px] text-rose-500" />
              Tren Detak Jantung
            </h3>
            <span className="text-xs font-medium text-on-surface-variant">rata-rata 78 bpm</span>
          </div>
          <div className="mt-3">
            <TrendChart data={heartRateTrend} unit="bpm" color="#e11d48" />
          </div>
        </section>

        <section className="rounded-2xl border border-surface-container-highest/60 bg-surface-container-lowest p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-on-surface">
              <Icon name="water_drop" className="text-[18px] text-sky-500" />
              Saturasi Oksigen
            </h3>
            <span className="text-xs font-medium text-on-surface-variant">rata-rata 98%</span>
          </div>
          <div className="mt-3">
            <TrendChart data={spo2Trend} unit="%" color="#0ea5e9" />
          </div>
        </section>

        <section className="rounded-2xl border border-surface-container-highest/60 bg-surface-container-lowest p-4 shadow-sm">
          <div className="flex items-center justify-between">
            <h3 className="flex items-center gap-1.5 text-sm font-semibold text-on-surface">
              <Icon name="directions_walk" className="text-[18px] text-emerald-600" />
              Aktivitas Fisik & Langkah
            </h3>
            <span className="text-xs font-medium text-on-surface-variant">total minggu ini</span>
          </div>
          <div className="mt-3">
            <TrendChart data={stepsTrend} unit="langkah" color="#059669" bar />
          </div>
        </section>
      </main>
    </>
  );
}
