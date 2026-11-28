'use client';

import { useState, type FormEvent } from 'react';
import { API_BASE } from '@/lib/api';
import Link from 'next/link';
import { reviewedMcuKey } from '@/lib/dailyBrief';

type Row = { group: string; label: string; value: string; unit: string; range: string; flag: string; page: number; source: string };
const empty: Row = { group: 'Other results', label: '', value: '', unit: '', range: '', flag: '', page: 0, source: '' };
const fields = { group: 'Section', label: 'Test name', value: 'Result', unit: 'Unit', range: 'Report range', flag: 'Report flag' } as const;

export default function McuPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [dateEvidence, setDateEvidence] = useState<{page: number; source: string}[]>([]);
  const [method, setMethod] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [labDate, setLabDate] = useState('');
  const [confirmed, setConfirmed] = useState(false);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    const file = new FormData(event.currentTarget).get('report');
    if (!(file instanceof File) || !file.size) return;
    setError('');
    setBusy(true);
    try {
      const response = await fetch((process.env.NEXT_PUBLIC_JAGSI_MCU_API ?? API_BASE) + '/api/mcu/extract', {
        method: 'POST', body: file, signal: AbortSignal.timeout(120000),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail);
      setRows(result.rows);
      setLabDate('');
      setDateEvidence(result.date_evidence);
      setMethod(result.methods.join(' + '));
      setConfirmed(false);
      if (!result.rows.length) setError('No supported results found. Enter results manually below.');
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Report processing failed.');
    } finally {
      setBusy(false);
    }
  }

  function continueSetup(includeReviewed = false) {
    sessionStorage.removeItem(reviewedMcuKey);
    if (includeReviewed && confirmed) {
      sessionStorage.setItem(reviewedMcuKey, JSON.stringify({
        lab_date: labDate || null,
        reviewed_rows: rows.map(({label, value, unit, flag}) => ({label, value, unit, flag})),
      }));
    }
    sessionStorage.setItem('jagsi-preview-intake', 'done');
    window.location.assign('/setup?step=guide');
  }

  return (
    <div className="onboarding-shell">
      <Link className="ungu-brand" href="/"><img src="/ungu/brand.svg" alt="" />JagSi</Link>
      <h1>Add an MCU report</h1>
      <p>Add sample results for the person wearing JagSi.</p>
      <div className="space-y-6">
        <form className="ungu-panel wrist-guide" onSubmit={upload}>
          <div className="wrist-guide-counter">02 / MCU intake</div>
          <img src="/ungu/report-scan.svg" width={302} height={160} alt="" />
          <h2>Upload MCU report</h2>
          <label htmlFor="report">Optional · PDF, JPEG, or PNG · up to 15 MB</label>
          <input id="report" name="report" type="file" accept=".pdf,.jpeg,.jpg,.png" required disabled={busy} className="max-w-full text-sm file:rounded-xl file:border-0 file:bg-white file:px-3 file:py-2 file:text-on-surface" />
          <button className="landing-cta justify-self-start" disabled={busy}>{busy ? 'Reading report…' : 'Scan report'}</button>
          <p role="status">{busy ? 'Extracting the report locally…' : method && 'Extraction method: ' + method}</p>
          {error && <p role="alert" className="rounded-xl bg-white p-3 text-error">{error}</p>}
        </form>
        <div className="ungu-panel">
        <button type="button" className="ungu-action" disabled={busy} onClick={() => { setRows([...rows, { ...empty }]); setConfirmed(false); }}>Enter results manually</button>
        <button type="button" className="ungu-action" disabled={busy} onClick={() => continueSetup()}>No results available yet</button>
        </div>
        {dateEvidence.length > 0 && <details className="ungu-panel"><summary>Dates found on the report</summary><ul>{dateEvidence.map((item, index) => <li key={index}>Page {item.page} · {item.source}</li>)}</ul></details>}
        {rows.length > 0 && <form className="ungu-panel ungu-history-tools" onSubmit={event => { event.preventDefault(); setConfirmed(true); }}>
          <h2>Review extracted results</h2>
          <label>Sample collection date (if known)<input type="date" value={labDate} onChange={event => { setLabDate(event.target.value); setConfirmed(false); }} /></label>
          {rows.map((row, index) => <fieldset key={index} disabled={busy} className="grid min-w-0 gap-3 rounded-xl border bg-white p-4 sm:grid-cols-2">
            <legend className="px-2 font-semibold">{row.group} · {row.label || 'New result'}</legend>
            {row.source && <p className="break-words text-sm sm:col-span-2">Page {row.page} · {row.source}</p>}
            {Object.entries(fields).map(([field, caption]) => {
              const key = field as keyof typeof fields;
              return <label key={field} className="grid gap-1 text-sm">{caption}
                <input className="min-w-0 rounded-md border p-2" value={row[key]} required={key === 'label' || key === 'value'} onChange={event => { setRows(rows.map((item, position) => position === index ? { ...item, [key]: event.target.value } : item)); setConfirmed(false); }} />
              </label>;
            })}
            <button type="button" className="ungu-action" onClick={() => { setRows(rows.filter((_, position) => position !== index)); setConfirmed(false); }}>Remove result</button>
          </fieldset>)}
          <button className="ungu-action" disabled={busy}>Confirm reviewed results</button>
          {confirmed && <>
            <p role="status">Review confirmed for this session.</p>
            <button type="button" className="landing-cta justify-self-start" onClick={() => continueSetup(true)}>Continue to smartband guide</button>
          </>}
        </form>}
      </div>
    </div>
  );
}
