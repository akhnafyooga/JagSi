/**
 * The audible and system-level half of an emergency alert (issue #13: "instant
 * visual/auditory alert trigger").
 *
 * The tone is generated with the Web Audio API instead of an audio file, so
 * there is nothing to download before the first alarm and nothing to 404.
 *
 * Browsers only allow sound after the user has interacted with the page, so the
 * dashboard shows an "Aktifkan suara" button that calls `unlock()` once. After
 * that, an alert that arrives while the caregiver is on another tab still rings.
 */

type AudioContextCtor = new () => AudioContext;

function audioContextCtor(): AudioContextCtor | null {
  if (typeof window === 'undefined') return null;
  const w = window as unknown as { AudioContext?: AudioContextCtor; webkitAudioContext?: AudioContextCtor };
  return w.AudioContext ?? w.webkitAudioContext ?? null;
}

export interface Alarm {
  /** Must be called from a click handler once; returns false if audio is unavailable. */
  unlock(): Promise<boolean>;
  start(): void;
  stop(): void;
  readonly ringing: boolean;
}

const BEEP_EVERY_MS = 1200;
const VIBRATE_PATTERN = [400, 200, 400, 200, 400];

export function createAlarm(): Alarm {
  let ctx: AudioContext | null = null;
  let timer: ReturnType<typeof setInterval> | null = null;

  const beep = () => {
    if (ctx && ctx.state === 'running') {
      // Two falling tones, loud enough to hear from another room on a phone
      // speaker, short enough not to clip.
      [880, 660].forEach((freq, i) => {
        const osc = ctx!.createOscillator();
        const gain = ctx!.createGain();
        const t0 = ctx!.currentTime + i * 0.28;
        osc.type = 'square';
        osc.frequency.value = freq;
        gain.gain.setValueAtTime(0.0001, t0);
        gain.gain.exponentialRampToValueAtTime(0.25, t0 + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.25);
        osc.connect(gain).connect(ctx!.destination);
        osc.start(t0);
        osc.stop(t0 + 0.26);
      });
    }
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      navigator.vibrate(VIBRATE_PATTERN);
    }
  };

  return {
    async unlock() {
      const Ctor = audioContextCtor();
      if (!Ctor) return false;
      try {
        ctx = ctx ?? new Ctor();
        if (ctx.state === 'suspended') await ctx.resume();
        return ctx.state === 'running';
      } catch {
        return false;
      }
    },
    start() {
      if (timer !== null) return;
      beep();
      timer = setInterval(beep, BEEP_EVERY_MS);
    },
    stop() {
      if (timer !== null) clearInterval(timer);
      timer = null;
      if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
        navigator.vibrate(0);
      }
    },
    get ringing() {
      return timer !== null;
    },
  };
}

export type NotificationState = 'granted' | 'denied' | 'default' | 'unsupported';

export function notificationState(): NotificationState {
  if (typeof window === 'undefined' || typeof Notification === 'undefined') return 'unsupported';
  return Notification.permission;
}

export async function requestNotificationPermission(): Promise<NotificationState> {
  if (notificationState() === 'unsupported') return 'unsupported';
  try {
    return await Notification.requestPermission();
  } catch {
    return notificationState();
  }
}

/**
 * Shows a system notification so the alert is seen even when the dashboard tab
 * is in the background. `tag` is the alert id: a re-sent alert replaces its
 * notification instead of stacking a second one.
 */
export function showSystemNotification(title: string, body: string, tag: string): boolean {
  if (notificationState() !== 'granted') return false;
  try {
    const n = new Notification(title, { body, tag, requireInteraction: true });
    n.onclick = () => {
      window.focus();
      n.close();
    };
    return true;
  } catch {
    return false;
  }
}

const SOUND_KEY = 'jagsi.alarmSound';

/** Remembered per browser. Storage can be unavailable (private mode), so it never throws. */
export function loadSoundPreference(): boolean {
  try {
    return window.localStorage.getItem(SOUND_KEY) !== 'off';
  } catch {
    return true;
  }
}

export function saveSoundPreference(on: boolean): void {
  try {
    window.localStorage.setItem(SOUND_KEY, on ? 'on' : 'off');
  } catch {
    /* preference simply is not remembered */
  }
}
