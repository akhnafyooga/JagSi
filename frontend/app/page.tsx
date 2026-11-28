import Link from 'next/link';

const features = [
  { title: 'Pemantauan vital', description: 'Detak, oksigen, dan suhu.', href: '/beranda#tanda-vital' },
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
      <div className="landing-night landing-cover">
        <header className="landing-container landing-header">
          <a className="ungu-brand" href="/"><img src="/ungu/brand.svg" alt="" />JagSi</a>
          <Link href="/setup" className="landing-cta">Set up JagSi</Link>
        </header>
        <section className="landing-container landing-hero">
          <div>
            <small>JagSi Watch · Data simulasi</small>
            <h1>Pantau orang <em>tersayang.</em></h1>
            <p>Tanda vital, tren, dan peringatan dalam satu tempat — untuk keluarga yang menjaga dari jauh.</p>
            <Link className="landing-cta" href="/beranda">Buka dashboard →</Link>
          </div>
          <div className="landing-watch" aria-label="Contoh pembacaan JagSi Watch">
            <div className="watch-strap" />
            <div className="watch-face"><small>Detak</small><strong>94 <span>bpm</span></strong><img src="/ungu/pulse.svg" alt="" /><small>09.42 · Simulasi</small></div>
            <div className="watch-card watch-oxygen"><small>Oksigen darah</small><strong>98%</strong></div>
            <div className="watch-card watch-temp"><small>Suhu tubuh</small><strong>36,6 °C</strong></div>
            <div className="watch-card watch-alert"><small>Peringatan</small><strong>Belum ada SOS</strong><span>Aman</span></div>
          </div>
        </section>
      </div>
      <div className="landing-container landing-content">
        <section>
          <h2>Yang bisa Anda pantau</h2>
          <p>Tiga hal yang paling sering ditanyakan keluarga, dari satu jam tangan.</p>
          <div className="landing-features">
            {features.map(({title,description,href}) => <article key={href}><h3>{title}</h3><p>{description}</p><Link href={href}>Lihat fitur <span aria-hidden="true">→</span><span className="sr-only"> {title}</span></Link></article>)}
          </div>
        </section>
        <section className="landing-steps">
          <h2>Dari sensor ke tindakan</h2>
          <ol>{steps.map((step,i) => <li key={step}><img src="/ungu/brand.svg" alt="" /><h3>{['Pantau pembacaan','Pahami perubahan','Tinjau kejadian'][i]}</h3><p>{step}</p></li>)}</ol>
        </section>
      </div>
      <footer className="landing-night"><div className="landing-container landing-header"><Link className="ungu-brand" href="/"><img src="/ungu/brand.svg" alt="" />JagSi</Link><span>Data simulasi · 2026</span></div></footer>
    </>
  );
}
