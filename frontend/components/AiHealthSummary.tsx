import { Icon } from './Icon';
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
    <section className="ungu-panel ungu-insight">
      <h2 className="ungu-panel-title"><Icon name="auto_awesome" />Ringkasan AI</h2>
            {text.startsWith('- **') ? (
        <ul className="ungu-insight-copy list-disc space-y-2 pl-5" aria-live="polite">
          {text.split('\n').map((line, index) => {
            const match = /^- \*\*(.*?)\*\* (.*)$/.exec(line);
            return <li key={index}>{match ? <><strong>{match[1]}</strong> {match[2]}</> : line}</li>;
          })}
        </ul>
      ) : <p className="ungu-insight-copy" aria-live="polite">{text}</p>}
      <small>{model}{simulated && ' · Simulasi'} {updatedAt}</small>
      <div className="flex flex-wrap gap-3">
      {onRefresh && <button className="ungu-action" onClick={onRefresh} disabled={loading}>Perbarui ringkasan</button>}
      <Link className="ungu-action" href="/riwayat">Lihat riwayat</Link>
      </div>
    </section>
  );
}
