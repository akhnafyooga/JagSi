import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { FakeSocket, createFakeSocket, makeAlert } from '@/test/fakeSocket';

import { useEmergencyAlerts } from '../useEmergencyAlerts';

beforeEach(() => FakeSocket.reset());
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function setup(onNewAlert = vi.fn()) {
  const hook = renderHook(() => useEmergencyAlerts({ createSocket: createFakeSocket, url: 'ws://test/ws/alerts', onNewAlert }));
  const socket = FakeSocket.latest();
  act(() => socket.open());
  return { hook, socket, onNewAlert };
}

describe('useEmergencyAlerts', () => {
  it('shows alerts that were already open when the dashboard connected', () => {
    const { hook, socket, onNewAlert } = setup();
    act(() => socket.receive({ type: 'hello', data: { at: 'x', open_alerts: [makeAlert()] } }));
    expect(hook.result.current.connection).toBe('live');
    expect(hook.result.current.open).toHaveLength(1);
    // The snapshot is not "new": no second notification for an old alert.
    expect(onNewAlert).not.toHaveBeenCalled();
  });

  it('reports each new alert once', () => {
    const { hook, socket, onNewAlert } = setup();
    const alert = makeAlert({ alert_id: 'fall-1' });
    act(() => socket.receive({ type: 'alert', data: alert }));
    act(() => socket.receive({ type: 'alert', data: alert }));
    expect(onNewAlert).toHaveBeenCalledTimes(1);
    expect(hook.result.current.open.map((a) => a.alert_id)).toEqual(['fall-1']);
    expect(hook.result.current.revision).toBe(2);
  });

  it('sends the acknowledgement on the socket and clears the alert when the server confirms', async () => {
    const { hook, socket } = setup();
    act(() => socket.receive({ type: 'alert', data: makeAlert({ alert_id: 'fall-2' }) }));

    await act(() => hook.result.current.acknowledge('fall-2'));
    expect(socket.sent).toContainEqual({ type: 'ack', alert_id: 'fall-2' });
    expect(hook.result.current.pending).toEqual(['fall-2']);

    act(() => socket.receive({ type: 'alert_ack', data: { alert_id: 'fall-2', via: 'websocket' } }));
    expect(hook.result.current.open).toEqual([]);
    expect(hook.result.current.pending).toEqual([]);
  });

  it('closes the alert here when another caregiver handles it', () => {
    const { hook, socket } = setup();
    act(() => socket.receive({ type: 'alert', data: makeAlert({ alert_id: 'fall-3' }) }));
    act(() => socket.receive({ type: 'alert_ack', data: { alert_id: 'fall-3', via: 'api' } }));
    expect(hook.result.current.open).toEqual([]);
  });

  it('falls back to the REST endpoint when the socket is down', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal('fetch', fetchMock);
    const { hook, socket } = setup();
    act(() => socket.receive({ type: 'alert', data: makeAlert({ alert_id: 'fall-4' }) }));
    socket.readyState = 3; // dropped, reconnect not yet done

    await act(() => hook.result.current.acknowledge('fall-4'));
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/alerts/fall-4/ack'),
      expect.objectContaining({ method: 'POST' }),
    );
    expect(hook.result.current.open).toEqual([]);
  });

  it('keeps the alert and shows an error when the REST fallback also fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 503 }));
    const { hook, socket } = setup();
    act(() => socket.receive({ type: 'alert', data: makeAlert({ alert_id: 'fall-5' }) }));
    socket.readyState = 3;

    await act(() => hook.result.current.acknowledge('fall-5'));
    expect(hook.result.current.open).toHaveLength(1);
    expect(hook.result.current.error).toContain('503');
    expect(hook.result.current.pending).toEqual([]);
  });

  it('reconnects with back-off after the connection drops', () => {
    vi.useFakeTimers();
    const { hook, socket } = setup();
    act(() => socket.close());
    expect(hook.result.current.connection).toBe('reconnecting');
    expect(FakeSocket.instances).toHaveLength(1);

    act(() => vi.advanceTimersByTime(1000));
    expect(FakeSocket.instances).toHaveLength(2);
    act(() => FakeSocket.latest().open());
    expect(hook.result.current.connection).toBe('live');
  });

  it('pings so a dead connection is noticed', () => {
    vi.useFakeTimers();
    const { socket } = setup();
    act(() => vi.advanceTimersByTime(25_000));
    expect(socket.sent).toContainEqual({ type: 'ping' });
  });

  it('closes the socket when the dashboard unmounts', () => {
    const { hook, socket } = setup();
    hook.unmount();
    expect(socket.readyState).toBe(3);
  });
});
