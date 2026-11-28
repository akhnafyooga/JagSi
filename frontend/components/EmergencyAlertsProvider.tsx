'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';

import type { ApiAlert } from '@/lib/api';
import {
  createAlarm,
  loadSoundPreference,
  notificationState,
  requestNotificationPermission,
  saveSoundPreference,
  showSystemNotification,
  type Alarm,
  type NotificationState,
} from '@/lib/alarm';
import { describeAlert } from '@/lib/realtime';
import { useCaregiverProfile } from '@/lib/useCaregiverProfile';
import { useEmergencyAlerts, type EmergencyAlerts } from '@/lib/useEmergencyAlerts';

import { EmergencyAlertOverlay } from './EmergencyAlertOverlay';

export interface EmergencyAlertContext extends EmergencyAlerts {
  /** The caregiver wants the alarm to ring (remembered per browser). */
  soundOn: boolean;
  /** The browser has allowed audio (needs one click on the page). */
  soundReady: boolean;
  notifications: NotificationState;
  /** One click that unlocks audio and asks for notification permission. */
  enableAlerts(): Promise<void>;
  setSoundOn(on: boolean): void;
}

const Ctx = createContext<EmergencyAlertContext | null>(null);

/** Reads the shared alert state. Outside the provider (tests, storybook) it returns null. */
export function useEmergencyAlertContext(): EmergencyAlertContext | null {
  return useContext(Ctx);
}

interface ProviderProps {
  children: React.ReactNode;
  /** Fallback name shown before sign-in or when auth is unconfigured. */
  elderName: string;
  /** For tests. */
  alarm?: Alarm;
  createSocket?: (url: string) => WebSocket;
}

/**
 * Owns the single alert WebSocket for the whole app (issue #13), so the
 * emergency screen appears on every page, not just the one that fetched alerts.
 */
export function EmergencyAlertsProvider({ children, elderName, alarm, createSocket }: ProviderProps) {
  const profile = useCaregiverProfile();
  const displayName = profile.wearerName ?? elderName;
  const alarmRef = useRef<Alarm | null>(alarm ?? null);
  const getAlarm = useCallback(() => {
    if (!alarmRef.current) alarmRef.current = createAlarm();
    return alarmRef.current;
  }, []);

  const [soundOn, setSoundOnState] = useState(true);
  const [soundReady, setSoundReady] = useState(false);
  const [ringing, setRinging] = useState(false);
  const [notifications, setNotifications] = useState<NotificationState>('unsupported');

  useEffect(() => {
    setSoundOnState(loadSoundPreference());
    setNotifications(notificationState());
  }, []);

  const soundOnRef = useRef(soundOn);
  soundOnRef.current = soundOn;

  const ring = useCallback(() => {
    if (!soundOnRef.current) return;
    getAlarm().start();
    setRinging(true);
  }, [getAlarm]);

  const silence = useCallback(() => {
    alarmRef.current?.stop();
    setRinging(false);
  }, []);

  const onNewAlert = useCallback(
    (alert: ApiAlert) => {
      ring();
      // The overlay covers the page when it is visible; a system notification
      // matters when the caregiver is on another tab or app.
      if (typeof document !== 'undefined' && document.hidden) {
        const copy = describeAlert(alert, displayName);
        showSystemNotification(copy.title, copy.body, alert.alert_id);
      }
    },
    [ring, displayName],
  );

  const alerts = useEmergencyAlerts({ onNewAlert, createSocket });

  // Alerts that were already open when the page loaded (hello snapshot) ring too,
  // once audio is unlocked; and the alarm stops as soon as nothing is open.
  useEffect(() => {
    if (alerts.open.length === 0) silence();
    else if (soundReady && !ringing && soundOn) ring();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [alerts.open.length, soundReady]);

  useEffect(() => () => alarmRef.current?.stop(), []);

  const enableAlerts = useCallback(async () => {
    setSoundReady(await getAlarm().unlock());
    setNotifications(await requestNotificationPermission());
  }, [getAlarm]);

  const setSoundOn = useCallback(
    (on: boolean) => {
      setSoundOnState(on);
      saveSoundPreference(on);
      if (!on) silence();
    },
    [silence],
  );

  const value = useMemo<EmergencyAlertContext>(
    () => ({ ...alerts, soundOn, soundReady, notifications, enableAlerts, setSoundOn }),
    [alerts, soundOn, soundReady, notifications, enableAlerts, setSoundOn],
  );

  const current = alerts.open[0];

  return (
    <Ctx.Provider value={value}>
      {children}
      {current ? (
        <EmergencyAlertOverlay
          alert={current}
          others={alerts.open.length - 1}
          elderName={displayName}
          pending={alerts.pending.includes(current.alert_id)}
          ringing={ringing}
          onAcknowledge={(id) => void alerts.acknowledge(id)}
          onMute={silence}
        />
      ) : null}
    </Ctx.Provider>
  );
}
