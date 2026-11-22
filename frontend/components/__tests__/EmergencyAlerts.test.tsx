import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { Alarm } from '@/lib/alarm';
import { FakeSocket, createFakeSocket, makeAlert } from '@/test/fakeSocket';

import { EmergencyAlertsProvider } from '../EmergencyAlertsProvider';
import { LiveFallStatus } from '../LiveFallStatus';
import { NotificationBell } from '../NotificationBell';

vi.mock('next/link', () => ({
  default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
    <a href={href} {...rest}>
      {children}
    </a>
  ),
}));

function fakeAlarm() {
  let ringing = false;
  return {
    unlock: vi.fn().mockResolvedValue(true),
    start: vi.fn(() => {
      ringing = true;
    }),
    stop: vi.fn(() => {
      ringing = false;
    }),
    get ringing() {
      return ringing;
    },
  } satisfies Alarm;
}

function renderApp(alarm = fakeAlarm()) {
  render(
    <EmergencyAlertsProvider elderName="Ibu Sari" alarm={alarm} createSocket={createFakeSocket}>
      <NotificationBell />
      <LiveFallStatus />
    </EmergencyAlertsProvider>,
  );
  const socket = FakeSocket.latest();
  act(() => {
    socket.open();
    socket.receive({ type: 'hello', data: { at: 'x', open_alerts: [] } });
  });
  return { alarm, socket };
}

beforeEach(() => FakeSocket.reset());
afterEach(() => {
  vi.unstubAllGlobals();
});

describe('emergency alerts on the dashboard', () => {
  it('shows "Aman" while nothing is open', () => {
    renderApp();
    expect(screen.getByText('Aman')).toBeInTheDocument();
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Notifikasi')).toBeInTheDocument();
  });

  it('a fall covers the screen, rings the alarm and updates the card and the bell', () => {
    const { alarm, socket } = renderApp();
    act(() => socket.receive({ type: 'alert', data: makeAlert({ alert_id: 'fall-1' }) }));

    expect(screen.getByRole('alertdialog')).toHaveTextContent('Ibu Sari kemungkinan terjatuh');
    // Vitals sent with the alert are shown, so the caregiver can judge urgency.
    expect(screen.getByRole('alertdialog')).toHaveTextContent('112');
    expect(alarm.start).toHaveBeenCalledTimes(1);
    expect(screen.getByText('Terdeteksi Jatuh')).toBeInTheDocument();
    expect(screen.getByLabelText('Notifikasi, 1 peringatan belum ditangani')).toBeInTheDocument();
  });

  it('SOS has its own wording', () => {
    const { socket } = renderApp();
    act(() => socket.receive({ type: 'alert', data: makeAlert({ alert_type: 'manual_sos' }) }));
    expect(screen.getByRole('alertdialog')).toHaveTextContent('Ibu Sari menekan tombol SOS');
    expect(screen.getByText('SOS Ditekan')).toBeInTheDocument();
  });

  it('"Saya tangani" acknowledges over the socket; the screen closes and the alarm stops', () => {
    const { alarm, socket } = renderApp();
    act(() => socket.receive({ type: 'alert', data: makeAlert({ alert_id: 'fall-2' }) }));

    fireEvent.click(screen.getByRole('button', { name: /Saya tangani/ }));
    expect(socket.sent).toContainEqual({ type: 'ack', alert_id: 'fall-2' });
    expect(screen.getByRole('button', { name: /Mengirim konfirmasi/ })).toBeDisabled();

    act(() => socket.receive({ type: 'alert_ack', data: { alert_id: 'fall-2', via: 'websocket' } }));
    expect(screen.queryByRole('alertdialog')).not.toBeInTheDocument();
    expect(alarm.stop).toHaveBeenCalled();
    expect(screen.getByText('Aman')).toBeInTheDocument();
  });

  it('muting stops the sound but the screen stays until someone handles it', () => {
    const { alarm, socket } = renderApp();
    act(() => socket.receive({ type: 'alert', data: makeAlert() }));

    fireEvent.click(screen.getByRole('button', { name: /Matikan suara/ }));
    expect(alarm.stop).toHaveBeenCalled();
    expect(screen.getByRole('alertdialog')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Suara mati/ })).toBeDisabled();
  });

  it('shows how many other alerts are waiting behind the current one', () => {
    const { socket } = renderApp();
    act(() => {
      socket.receive({ type: 'alert', data: makeAlert({ alert_id: 'a', received_at: '2026-11-17T13:00:00Z' }) });
      socket.receive({ type: 'alert', data: makeAlert({ alert_id: 'b', received_at: '2026-11-17T13:01:00Z' }) });
    });
    expect(screen.getByText('+1 peringatan lain menunggu')).toBeInTheDocument();
  });

  it('tells the caregiver when live alerts are not connected instead of saying "Aman"', () => {
    render(
      <EmergencyAlertsProvider elderName="Ibu Sari" alarm={fakeAlarm()} createSocket={createFakeSocket}>
        <LiveFallStatus />
      </EmergencyAlertsProvider>,
    );
    expect(screen.getByText('Menunggu koneksi')).toBeInTheDocument();
    expect(screen.queryByText('Aman')).not.toBeInTheDocument();
  });
});
