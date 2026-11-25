import Link from 'next/link';

const features = [
  { title: 'Pemantauan vital', description: 'Detak, oksigen, dan suhu.', href: '/monitoring' },
  { title: 'Ringkasan AI', description: 'Tren dari pembacaan sensor.', href: '/beranda' },
  { title: 'Peringatan keluarga', description: 'Tinjau kejadian SOS dan jatuh.', href: '/darurat' },
];

const steps = [
  'Pantau pembacaan dari JagSi Watch.',
  'Pahami perubahan dan waktu pengamatan.',
  'Tinjau sumber peringatan sebelum mengakuinya.',
];

export default function LandingPage() {
  return (
    <>
      <header className="mx-auto flex max-w-7xl items-center justify-between px-5 py-4">
        <Link href="/" className="text-xl font-bold text-primary">JagSi</Link>
        <Link href="/beranda" className="rounded-xl bg-primary px-4 py-3 font-semibold text-white">
          Buka dashboard
        </Link>
      </header>
      <section className="mx-auto grid max-w-7xl items-center gap-8 px-5 py-12 md:grid-cols-2 md:py-20">
        <div>
          <h1 className="jagsi-display text-5xl font-semibold tracking-tight md:text-7xl">Jaga Lansia</h1>
          <p className="mt-4 max-w-md text-lg text-on-surface-variant">
            Tanda vital, tren, dan peringatan dalam satu tempat — untuk keluarga yang menjaga dari jauh.
          </p>
          <Link href="/beranda" className="mt-6 inline-flex rounded-xl bg-primary px-5 py-3 font-semibold text-white">
            Buka dashboard <span aria-hidden="true" className="ml-2">→</span>
          </Link>
        </div>
        <div className="rounded-3xl bg-[#211637] p-6 text-white md:p-10">
          <p className="text-sm text-[#e8dfff]">JagSi Watch · Data simulasi</p>
          <p className="mt-5 text-sm">Detak jantung</p>
          <p className="jagsi-display text-7xl font-semibold">94 <span className="text-xl">bpm</span></p>
          <dl className="mt-6 grid grid-cols-2 gap-3">
            <div className="rounded-xl bg-[#33205a] p-4"><dt>Oksigen darah</dt><dd>98%</dd></div>
            <div className="rounded-xl bg-[#33205a] p-4"><dt>Suhu tubuh</dt><dd>36,6 °C</dd></div>
          </dl>
          <p className="mt-4 text-sm">Peringatan · Belum ada SOS</p>
        </div>
      </section>
      <section className="mx-auto max-w-7xl px-5 pb-12">
        <h2 className="jagsi-display text-3xl font-semibold">Yang bisa Anda pantau</h2>
        <div className="mt-5 grid gap-4 md:grid-cols-3">
          {features.map(({ title, description, href }) => (
            <Link key={href} href={href} className="rounded-2xl border border-surface-container-highest bg-white p-5 hover:border-primary">
              <h3 className="text-xl font-semibold">{title}</h3>
              <p className="mt-2 text-on-surface-variant">{description}</p>
              <span className="mt-4 block font-semibold text-primary">Lihat fitur →</span>
            </Link>
          ))}
        </div>
      </section>
      <section className="bg-primary-container">
        <div className="mx-auto max-w-7xl px-5 py-10">
          <h2 className="jagsi-display text-3xl font-semibold">Dari sensor ke tindakan</h2>
          <ol className="mt-5 grid list-inside list-decimal gap-4 md:grid-cols-3">
            {steps.map((step) => <li key={step} className="rounded-xl bg-white p-4">{step}</li>)}
          </ol>
        </div>
      </section>
      <footer className="mx-auto max-w-7xl px-5 py-6 text-sm">JagSi · Data simulasi</footer>
    </>
  );
}
