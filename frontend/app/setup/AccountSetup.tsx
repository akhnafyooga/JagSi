'use client';

import { createClient } from '@supabase/supabase-js';
import { type FormEvent, useEffect, useState } from 'react';
import Link from 'next/link';
import { API_BASE, DEVICE_ID } from '@/lib/api';

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
const auth = url && key ? createClient(url, key, { auth: { flowType: 'pkce' } }).auth : null;
const preview = process.env.NEXT_PUBLIC_JAGSI_PAIRING_PREVIEW === '1';

export function AccountSetup() {
  const [step, setStep] = useState(0);
  const [name, setName] = useState('');
  const [wearer, setWearer] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!auth) return;
    const { data } = auth.onAuthStateChange((event, session) => {
      if (event !== 'INITIAL_SESSION' && event !== 'SIGNED_IN') return;
      if (!session) return;
      const profile = session.user.user_metadata;
      setName(profile.caregiver_name ?? profile.full_name ?? '');
      setWearer(profile.wearer_name ?? '');
      setStep(profile.wearer_name ? 3 : profile.caregiver_name ? 2 : 1);
    });
    if (new URLSearchParams(location.search).has('error')) {
      setError('Masuk dengan Google gagal. Silakan coba lagi.');
    }
    return () => data.subscription.unsubscribe();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    setError('');
    setBusy(true);
    try {
      if (step === 0) {
        if (!auth) throw new Error('Konfigurasi Google belum tersedia.');
        const result = await auth.signInWithOAuth({ provider: 'google',
          options: { redirectTo: location.origin + '/setup' } });
        if (result.error) throw result.error;
      } else if (step < 3) {
        const value = (step === 1 ? name : wearer).trim();
        if (!value) throw new Error('Masukkan nama yang valid.');
        const data = step === 1 ? { caregiver_name: value } :
          { wearer_name: value, wearer_relationship: fields.get('relationship'), monitoring_consent: true };
        if (auth) {
          const result = await auth.updateUser({ data });
          if (result.error) throw result.error;
        }
        setStep(step + 1);
      } else {
        if (!preview) throw new Error('Pemasangan perangkat fisik belum tersedia.');
        const response = await fetch(API_BASE + '/api/demo-pair', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code: String(fields.get('code')).trim() }),
        });
        if (response.status === 409) { setStep(5); return; }
        if (!response.ok) throw new Error('Pemasangan gagal. Periksa koneksi API.');
        const result = await response.json();
        if (result.device_id !== DEVICE_ID) throw new Error('Perangkat berbeda dari konfigurasi dashboard.');
        setStep(4);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Terjadi kesalahan.');
    } finally { setBusy(false); }
  }

  const headings = ['Pantau orang tersayang.', 'Akun pengasuh', 'Siapa yang memakai JagSi?',
    'Pasangkan smartband', 'Siap menerima bacaan', 'Periksa kode pemasangan'];
  const descriptions = ['Gunakan akun Google untuk membuat atau membuka akun pengasuh.',
    'Isi nama yang akan ditampilkan di akun Anda.', 'Pilih siapa yang akan mengenakan smartband.',
    `Masukkan kode pemasangan untuk smartband yang akan digunakan ${wearer}.`,
    `Smartband simulasi terhubung untuk sesi ${wearer}.`, 'Minta kode baru dari panel simulasi lalu coba lagi.'];
  const actions = ['Lanjutkan dengan Google', 'Simpan dan lanjutkan', 'Simpan profil',
    'Hubungkan perangkat', 'Lanjut ke hasil MCU', 'Coba lagi'];

  return <main className={`account-setup ${step === 0 ? 'account-signin' : ''}`}>
    <Link className="ungu-brand" href="/"><img src="/ungu/brand.svg" alt="" width="28" height="28" />JagSi</Link>
    {(step === 0 || step >= 3) && <div className="account-hero">
      <img src={step === 0 ? '/ungu/auth-pulse.svg' : '/ungu/auth-band.svg'} alt="" width="160" height="120" />
    </div>}
    <form key={step} onSubmit={submit}>
      <h1>{headings[step]}</h1><p>{descriptions[step]}</p>
      {step === 1 && <label>Nama lengkap<input autoComplete="name" required maxLength={100} value={name} onChange={event => setName(event.target.value)} /></label>}
      {step === 2 && <>
        <label>Nama pemakai<input required maxLength={100} value={wearer} onChange={event => setWearer(event.target.value)} /></label>
        <label>Hubungan dengan Anda<select name="relationship" defaultValue="" required>
          <option value="" disabled>Pilih hubungan</option><option>Orang tua</option><option>Kakek atau nenek</option><option>Lainnya</option>
        </select></label>
        <label className="account-consent"><input type="checkbox" required /> Pemakai menyetujui pemantauan.</label>
      </>}
      {(step === 3 || step === 5) && <label>Kode pemasangan<input name="code" required maxLength={32} autoComplete="off" /></label>}
      {step === 4 ? <Link className="account-action" href="/mcu?setup=1">{actions[step]} <img src="/ungu/auth-arrow.svg" alt="" /></Link> :
        <button className="account-action" disabled={busy || (step === 0 && !auth)}>{busy ? 'Memproses…' : actions[step]} <img src="/ungu/auth-arrow.svg" alt="" /></button>}
      {step === 0 && !auth && <p>Google belum dikonfigurasi.</p>}
      {step === 0 && preview && <button type="button" className="ungu-action" onClick={() => setStep(1)}>Buka simulasi presentasi</button>}
      {step >= 3 && preview && <small>Mode simulasi · gunakan kode dari panel presentasi.</small>}
      {error && <p role="alert">{error}</p>}
    </form>
  </main>;
}
