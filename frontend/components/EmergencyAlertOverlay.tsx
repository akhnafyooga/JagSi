'use client';

import Link from 'next/link';

import { formatTimestamp, type ApiAlert } from '@/lib/api';
import { describeAlert } from '@/lib/realtime';

import { Icon } from './Icon';

interface EmergencyAlertOverlayProps {
  alert: ApiAlert;
  /** How many other alerts are also waiting. */
  others: number;
  elderName: string;
  pending: boolean;
  ringing: boolean;
  onAcknowledge(alertId: string): void;
  onMute(): void;
}

const VITAL_LABELS: Array<[string, string, string]> = [
  ['heart_rate', 'Detak jantung', 'bpm'],
  ['spo2', 'SpO₂', '%'],
  ['body_temperature', 'Suhu', '°C'],
];

/**
 * Full-screen emergency screen (issue #13).
 *
 * It covers whatever page the caregiver is on and stays until someone presses
 * "Saya tangani". Muting stops the sound only; the screen itself cannot be
 * closed without an acknowledgement, because a dismissed fall alert that nobody
 * handled is the failure this whole feature exists to prevent.
 */
export function EmergencyAlertOverlay({
  alert,
  others,
  elderName,
  pending,
  ringing,
  onAcknowledge,
  onMute,
}: EmergencyAlertOverlayProps) {
  const copy = describeAlert(alert, elderName);
  const vitals = alert.vitals ?? {};
  const shownVitals = VITAL_LABELS.filter(([key]) => typeof vitals[key] === 'number');

  return (
    <div className="fixed inset-0 z-[60] grid place-items-center overflow-y-auto bg-black/60 p-3">
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="emergency-title"
        aria-describedby="emergency-body"
        className="ungu-emergency w-full max-w-[390px] rounded-3xl bg-[#211337] p-6 text-[#f4eeff]"
      >
        <div className="flex items-center justify-between text-xs font-semibold uppercase tracking-wider">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-2 w-2 animate-pulse rounded-full bg-on-error" />
            Peringatan darurat
          </span>
          <span>Diterima {formatTimestamp(alert.received_at)}</span>
        </div>

        <div className="mt-4 flex flex-col items-start">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-on-error/15 ring-4 ring-on-error/40">
            <Icon name={copy.icon} filled className="text-[24px]" />
          </div>
          <h2 id="emergency-title" className="mt-6 text-2xl font-bold leading-tight">
            {copy.title}
          </h2>
          <p id="emergency-body" className="mt-2 text-sm leading-relaxed text-on-error/90">
            {copy.body}
          </p>
        </div>

        {shownVitals.length > 0 ? (
          <dl className="mt-6 grid grid-cols-3 gap-2 rounded-2xl bg-on-error/10 p-3 text-center">
            {shownVitals.map(([key, label, unit]) => (
              <div key={key}>
                <dt className="text-[11px] text-on-error/80">{label}</dt>
                <dd className="text-lg font-semibold">
                  {vitals[key]}
                  <span className="ml-0.5 text-xs font-normal">{unit}</span>
                </dd>
              </div>
            ))}
          </dl>
        ) : null}

        {others > 0 ? (
          <p className="mt-4 text-center text-xs font-medium">+{others} peringatan lain menunggu</p>
        ) : null}

        <div className="ungu-emergency-actions">
          <button
            type="button"
            onClick={() => onAcknowledge(alert.alert_id)}
            disabled={pending}
            className="flex w-full items-center justify-center gap-2 rounded-2xl bg-on-error py-4 text-base font-bold text-error shadow-lg transition-transform active:scale-[0.98] disabled:opacity-70"
          >
            <Icon name="check_circle" filled className="text-[22px]" />
            {pending ? 'Mengirim konfirmasi…' : 'Saya tangani'}
          </button>
          <div className="contents">
            <a
              href="tel:119"
              className="flex items-center justify-center gap-1.5 rounded-2xl border border-on-error/60 py-3 text-sm font-semibold"
            >
              <Icon name="call" className="text-[18px]" />
              Panggil 119
            </a>
            <button
              type="button"
              onClick={onMute}
              disabled={!ringing}
              className="flex items-center justify-center gap-1.5 rounded-2xl border border-on-error/60 py-3 text-sm font-semibold disabled:opacity-50"
            >
              <Icon name={ringing ? 'volume_off' : 'notifications_off'} className="text-[18px]" />
              {ringing ? 'Matikan suara' : 'Suara mati'}
            </button>
          </div>
          <Link href="/darurat" className="block text-center text-xs font-medium underline underline-offset-2">
            Lihat semua peringatan
          </Link>
        </div>
      </div>
    </div>
  );
}
