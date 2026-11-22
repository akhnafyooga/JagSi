'use client';

import { useEffect, useState } from 'react';

import { fetchAlerts, formatTimestamp, toAlertItem, type ApiAlert } from '@/lib/api';
import { alerts as mockAlerts } from '@/lib/mock-data';
import { cn } from '@/lib/utils';

import { useEmergencyAlertContext } from './EmergencyAlertsProvider';
import { Icon } from './Icon';

const toneMap = {
  warning: { box: 'border-amber-200/60 bg-amber-50/60', icon: 'bg-amber-100 text-amber-700' },
  critical: { box: 'border-error/25 bg-error/5', icon: 'bg-error/10 text-error' },
  info: { box: 'border-sky-200/60 bg-sky-50/60', icon: 'bg-sky-100 text-sky-700' },
} as const;

/**
 * Alert history on the Darurat page, from the backend (issue #13).
 *
 * It refetches whenever the alert socket reports a new alert or an
 * acknowledgement, so the list and the emergency screen never disagree. When
 * the backend is unreachable it falls back to the issue #12 demo list and says
 * so, the same rule the vital cards follow.
 */
export function LiveAlertLog() {
  const ctx = useEmergencyAlertContext();
  const revision = ctx?.revision ?? 0;
  const [rows, setRows] = useState<ApiAlert[] | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetchAlerts(20, controller.signal)
      .then(({ alerts }) => {
        setRows(alerts);
        setFailed(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, [revision]);

  if (failed && rows === null) {
    return (
      <section className="space-y-2">
        <Header badge="Data demo" />
        <p className="text-[11px] text-on-surface-variant">
          Backend belum terhubung. Daftar di bawah adalah contoh, bukan peringatan dari perangkat.
        </p>
        <div className="space-y-2">
          {mockAlerts.map((a) => (
            <Row key={a.id} icon={a.icon} tone={a.tone} title={a.title} description={a.description} time={a.time} />
          ))}
        </div>
      </section>
    );
  }

  if (rows === null) {
    return (
      <section className="space-y-2">
        <Header />
        <p className="text-xs text-on-surface-variant">Memuat…</p>
      </section>
    );
  }

  return (
    <section className="space-y-2">
      <Header />
      {rows.length === 0 ? (
        <p className="rounded-2xl border border-surface-container-highest/60 bg-surface-container-lowest p-4 text-center text-xs text-on-surface-variant">
          Belum ada peringatan dari perangkat.
        </p>
      ) : (
        <div className="space-y-2">
          {rows.map((alert) => {
            const item = toAlertItem(alert);
            const open = alert.status === 'unresolved';
            const pending = ctx?.pending.includes(alert.alert_id) ?? false;
            return (
              <Row
                key={alert.alert_id}
                icon={item.icon}
                tone={item.tone}
                title={item.title}
                description={`${item.description} · ${open ? 'Belum ditangani' : 'Sudah ditangani'}`}
                time={formatTimestamp(alert.received_at)}
                action={
                  open && ctx ? (
                    <button
                      type="button"
                      disabled={pending}
                      onClick={() => void ctx.acknowledge(alert.alert_id)}
                      className="mt-2 rounded-lg bg-error px-3 py-1.5 text-xs font-semibold text-on-error disabled:opacity-60"
                    >
                      {pending ? 'Mengirim…' : 'Saya tangani'}
                    </button>
                  ) : null
                }
              />
            );
          })}
        </div>
      )}
    </section>
  );
}

function Header({ badge }: { badge?: string }) {
  return (
    <div className="flex items-center justify-between">
      <h2 className="text-base font-semibold tracking-tight text-on-surface">Riwayat Peringatan</h2>
      {badge ? (
        <span className="rounded-md bg-surface-container-high px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-on-surface-variant">
          {badge}
        </span>
      ) : null}
    </div>
  );
}

interface RowProps {
  icon: string;
  tone: keyof typeof toneMap;
  title: string;
  description: string;
  time: string;
  action?: React.ReactNode;
}

function Row({ icon, tone, title, description, time, action }: RowProps) {
  const t = toneMap[tone];
  return (
    <article className={cn('flex items-start gap-3 rounded-2xl border p-3.5', t.box)}>
      <div className={cn('flex h-9 w-9 shrink-0 items-center justify-center rounded-full', t.icon)}>
        <Icon name={icon} className="text-[20px]" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-on-surface">{title}</h3>
          <span className="shrink-0 text-[11px] font-medium text-on-surface-variant">{time}</span>
        </div>
        <p className="mt-0.5 text-xs text-on-surface-variant">{description}</p>
        {action}
      </div>
    </article>
  );
}
