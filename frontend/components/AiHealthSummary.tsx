import Link from 'next/link';

interface AiHealthSummaryProps {
  text: string;
  /** Where the text came from, e.g. "Gemini · gemini-3.8-flash" or "Data demo". */
  model: string;
  updatedAt: string;
  loading?: boolean;
  /** Shows a short note that some numbers behind the summary are simulated. */
  simulated?: boolean;
  onRefresh?: () => void;
}

export function AiHealthSummary({
  text,
  model,
  updatedAt,
  loading = false,
  simulated = false,
  onRefresh,
}: AiHealthSummaryProps) {
  return (
    <section className="ungu-panel ungu-summary">
      <h2>Ringkasan AI</h2>
      <p aria-live="polite">{text}</p>
      <small>{model}{simulated && ' · Simulasi'} {updatedAt}</small>
      {onRefresh && <button className="ungu-action" onClick={onRefresh} disabled={loading}>Perbarui ringkasan</button>}
      <Link className="ungu-action" href="/riwayat">Lihat riwayat</Link>
    </section>
  );
}
