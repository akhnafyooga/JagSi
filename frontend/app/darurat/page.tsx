import { TopAppBar } from '@/components/TopAppBar';
import { Icon } from '@/components/Icon';
import { alerts, elder } from '@/lib/mock-data';

const toneMap = {
  warning: { box: 'border-amber-200/60 bg-amber-50/60', icon: 'bg-amber-100 text-amber-700' },
  critical: { box: 'border-error/25 bg-error/5', icon: 'bg-error/10 text-error' },
  info: { box: 'border-sky-200/60 bg-sky-50/60', icon: 'bg-sky-100 text-sky-700' },
} as const;

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

        {/* Alert log */}
        <section className="space-y-2">
          <h2 className="text-base font-semibold tracking-tight text-on-surface">Riwayat Peringatan</h2>
          <div className="space-y-2">
            {alerts.map((a) => {
              const tone = toneMap[a.tone];
              return (
                <article
                  key={a.id}
                  className={`flex items-start gap-3 rounded-2xl border p-3.5 ${tone.box}`}
                >
                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${tone.icon}`}>
                    <Icon name={a.icon} className="text-[20px]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <h3 className="text-sm font-semibold text-on-surface">{a.title}</h3>
                      <span className="shrink-0 text-[11px] font-medium text-on-surface-variant">
                        {a.time}
                      </span>
                    </div>
                    <p className="mt-0.5 text-xs text-on-surface-variant">{a.description}</p>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </main>
    </>
  );
}
