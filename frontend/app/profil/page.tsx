import { TopAppBar } from '@/components/TopAppBar';
import { Icon } from '@/components/Icon';
import { elder, emergencyContacts, medications } from '@/lib/mock-data';

const sensors = [
  { name: 'Sensor Detak Jantung', icon: 'favorite', status: 'Aktif' },
  { name: 'Sensor SpO₂', icon: 'water_drop', status: 'Aktif' },
  { name: 'Sensor Suhu Tubuh', icon: 'thermostat', status: 'Aktif' },
  { name: 'Akselerometer & Giroskop', icon: 'sensors', status: 'Aktif' },
];

export default function ProfilPage() {
  return (
    <>
      <TopAppBar title="Profil & Sensor" subtitle={elder.name} online />

      <main className="space-y-4 px-4 pt-3">
        {/* Profile card */}
        <section className="rounded-2xl border border-surface-container-highest/60 bg-surface-container-lowest p-4 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary-container text-on-primary-container">
              <Icon name="person" className="text-[34px]" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-on-surface">{elder.fullName}</h2>
              <p className="text-sm text-on-surface-variant">
                {elder.age} tahun · {elder.gender}
              </p>
              <span className="mt-1 inline-block rounded-full bg-amber-50 px-2 py-0.5 text-xs font-medium text-amber-700">
                {elder.condition}
              </span>
            </div>
          </div>
          <dl className="mt-4 space-y-1.5 border-t border-surface-container-low pt-3 text-sm">
            <div className="flex justify-between">
              <dt className="text-on-surface-variant">Alamat</dt>
              <dd className="text-on-surface">{elder.address}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-on-surface-variant">Pengasuh utama</dt>
              <dd className="text-on-surface">{elder.caregiver}</dd>
            </div>
          </dl>
        </section>

        {/* Sensor status */}
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-on-surface">Status Sensor Smartwear</h3>
          <div className="space-y-2">
            {sensors.map((s) => (
              <div
                key={s.name}
                className="flex items-center justify-between rounded-xl border border-surface-container-highest/60 bg-surface-container-lowest px-3 py-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-surface-container text-on-surface-variant">
                    <Icon name={s.icon} className="text-[18px]" />
                  </div>
                  <span className="text-sm text-on-surface">{s.name}</span>
                </div>
                <span className="flex items-center gap-1 text-xs font-semibold text-emerald-700">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
                  {s.status}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Medication schedule */}
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-on-surface">Jadwal & Pengingat Obat</h3>
          <div className="space-y-2">
            {medications.map((m) => (
              <div
                key={m.id}
                className="flex items-center justify-between rounded-xl border border-surface-container-highest/60 bg-surface-container-lowest px-3 py-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary-container text-on-secondary-container">
                    <Icon name="medication" className="text-[18px]" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-on-surface">{m.name}</p>
                    <p className="text-xs text-on-surface-variant">
                      {m.dose} · {m.schedule}
                    </p>
                  </div>
                </div>
                <span
                  className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                    m.taken ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                  }`}
                >
                  {m.taken ? 'Diminum' : 'Belum'}
                </span>
              </div>
            ))}
          </div>
        </section>

        {/* Emergency contacts */}
        <section className="space-y-2">
          <h3 className="text-sm font-semibold text-on-surface">Kontak Darurat Terhubung</h3>
          <div className="space-y-2">
            {emergencyContacts.map((c) => (
              <div
                key={c.id}
                className="flex items-center justify-between rounded-xl border border-surface-container-highest/60 bg-surface-container-lowest px-3 py-2.5"
              >
                <div className="flex items-center gap-2.5">
                  <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-tertiary-container text-on-tertiary-container">
                    <Icon name="call" className="text-[18px]" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-on-surface">{c.name}</p>
                    <p className="text-xs text-on-surface-variant">{c.relation}</p>
                  </div>
                </div>
                <span className="text-sm font-medium text-primary">{c.phone}</span>
              </div>
            ))}
          </div>
        </section>

        {/* Settings */}
        <section className="space-y-2 pb-2">
          <h3 className="text-sm font-semibold text-on-surface">Pengaturan & Asisten AI</h3>
          <div className="rounded-xl border border-surface-container-highest/60 bg-surface-container-lowest px-3">
            {[
              { icon: 'notifications_active', label: 'Notifikasi Darurat', value: 'Aktif' },
              { icon: 'auto_awesome', label: 'Asisten JagSi AI', value: 'Aktif' },
              { icon: 'language', label: 'Bahasa', value: 'Indonesia' },
            ].map((row) => (
              <div
                key={row.label}
                className="flex items-center justify-between border-b border-surface-container-low py-2.5 last:border-b-0"
              >
                <div className="flex items-center gap-2.5">
                  <Icon name={row.icon} className="text-[18px] text-on-surface-variant" />
                  <span className="text-sm text-on-surface">{row.label}</span>
                </div>
                <span className="text-sm text-on-surface-variant">{row.value}</span>
              </div>
            ))}
          </div>
        </section>
      </main>
    </>
  );
}
