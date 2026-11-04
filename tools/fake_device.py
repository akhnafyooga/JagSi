"""Fake JagSi watch: publishes the same MQTT messages as the ESP32 firmware.

Use it to test the monitor / backend / dashboard without running Wokwi.
It follows the same rules as the firmware: retained status + Last Will,
telemetry every N seconds, events re-sent every 5 s until "ack_alert".

Examples:
    python fake_device.py                         # telemetry every 2 s, forever
    python fake_device.py --count 10 --sos-at 3   # 10 messages, SOS after the 3rd
    python fake_device.py --fall-at 5             # simulate a fall after the 5th
"""

import argparse
import collections
import json
import math
import os
import random
import threading
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

from jagsi_schema import topic

FW_VERSION = "0.1.0-fake"
ALERT_RESEND_S = 5
ALERT_MAX_ATTEMPTS = 5

# Motion window, must match backend/ml/schema.py
MOTION_SAMPLE_RATE_HZ = 10
MOTION_WINDOW_SIZE = 30          # 10 Hz * 3.0 s
MOTION_HOP_S = 1.0               # 10 new samples per publish


def still_sample(t):
    """Someone sitting or standing: 1 g down, small noise."""
    return [
        round(0.02 * math.sin(t * 2.0) + random.uniform(-0.01, 0.01), 2),
        round(0.02 * math.cos(t * 1.7) + random.uniform(-0.01, 0.01), 2),
        round(1.0 + random.uniform(-0.02, 0.02), 2),
        round(random.uniform(-1.0, 1.0), 1),
        round(random.uniform(-1.0, 1.0), 1),
        round(random.uniform(-1.0, 1.0), 1),
    ]


def walking_sample(t):
    """Gait: roughly 2 Hz oscillation around 1 g."""
    swing = 0.35 * math.sin(t * 12.6)
    return [
        round(0.15 * math.sin(t * 12.6) + random.uniform(-0.03, 0.03), 2),
        round(0.12 * math.cos(t * 12.6) + random.uniform(-0.03, 0.03), 2),
        round(1.0 + swing + random.uniform(-0.03, 0.03), 2),
        round(25.0 * math.sin(t * 12.6), 1),
        round(18.0 * math.cos(t * 12.6), 1),
        round(10.0 * math.sin(t * 6.3), 1),
    ]


def fall_samples():
    """Ten samples shaped like the synthetic falls the model was trained on:
    free fall (SMV under 0.5 g), impact spike (over 2 g), then lying still."""
    rows = [[0.05, 0.05, 0.15, 30.0, 20.0, 10.0] for _ in range(4)]
    rows.append([1.2, 1.5, 2.6, 250.0, 180.0, 120.0])
    rows.append([0.6, 0.7, 1.4, 90.0, 60.0, 40.0])
    rows += [[0.95, 0.1, 0.08, 0.5, 0.3, 0.2] for _ in range(4)]
    return rows


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeDevice:
    def __init__(self, args):
        self.a = args
        self.dev = args.device_id
        self.boot_id = f"{random.getrandbits(32):08x}"
        self.start = time.monotonic()
        self.seq = 0
        self.event_seq = 0
        self.interval = args.interval
        self.pending = {}          # event_id -> {"payload": dict, "attempts": int, "last": float}
        self.lock = threading.Lock()
        self.acked = []

        # Rolling motion window, same idea as MotionWindow in the firmware.
        self.motion_buf = collections.deque(maxlen=MOTION_WINDOW_SIZE)
        self.motion_seq = 0
        self.motion_enabled = not args.no_motion
        self.inject_fall = False   # set for one window when a fall is simulated

        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                                  client_id=f"{self.dev}-{self.boot_id}")
        self.client.will_set(topic(self.dev, "status"),
                             json.dumps({"device_id": self.dev, "state": "offline"}), qos=1, retain=True)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.connected = threading.Event()

    def uptime_ms(self):
        return int((time.monotonic() - self.start) * 1000)

    def vitals(self):
        t = time.monotonic() - self.start
        return {"heart_rate": int(75 + 5 * math.sin(t / 10)),
                "spo2": round(97 + 0.5 * math.sin(t / 7), 2),
                "body_temperature": round(36.6 + 0.1 * math.sin(t / 30), 2)}

    # --- MQTT -------------------------------------------------------------
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            print(f"[fake] connect failed: {reason_code}")
            return
        client.subscribe(topic(self.dev, "cmd"), qos=1)
        self.publish_status()
        print(f"[fake] {self.dev} connected to {self.a.host}:{self.a.port}")
        self.connected.set()

    def on_message(self, client, userdata, msg):
        try:
            cmd = json.loads(msg.payload)
        except ValueError:
            print("[fake] bad JSON command")
            return
        name = cmd.get("cmd")
        print(f"[fake] <- cmd {cmd}")
        if name == "ping":
            self.publish_status()
        elif name == "set_interval":
            ms = cmd.get("ms", 0)
            if isinstance(ms, int) and 1000 <= ms <= 60000:
                self.interval = ms / 1000
                self.publish_status()
        elif name == "set_motion":
            self.motion_enabled = bool(cmd.get("enabled", True))
            self.publish_status()
        elif name == "ack_alert":
            with self.lock:
                if self.pending.pop(cmd.get("event_id"), None) is not None:
                    self.acked.append(cmd["event_id"])
                    print(f"[fake] alert {cmd['event_id']} acknowledged")

    def publish(self, kind, payload, retain=False):
        self.client.publish(topic(self.dev, kind), json.dumps(payload), qos=0, retain=retain)

    def publish_status(self):
        self.publish("status", {"device_id": self.dev, "state": "online", "fw": FW_VERSION,
                                "battery_level": 87, "rssi": -60, "ip": "127.0.0.1",
                                "interval_ms": int(self.interval * 1000),
                                "motion_enabled": self.motion_enabled,
                                "sample_rate_hz": MOTION_SAMPLE_RATE_HZ}, retain=True)

    def publish_telemetry(self, peak_g=1.0):
        self.seq += 1
        payload = {"device_id": self.dev, "seq": self.seq, "ts": now_iso(), "uptime_ms": self.uptime_ms(),
                   **self.vitals(),
                   "accel": {"x": 0.0, "y": 0.0, "z": 1.0}, "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
                   "accel_peak_g": peak_g, "battery_level": 87, "sim": True}
        self.publish("telemetry", payload)
        print(f"[fake] -> telemetry #{self.seq}")

    def fill_motion(self):
        """Adds one hop (10 samples) of motion to the rolling window."""
        t = time.monotonic() - self.start
        if self.inject_fall:
            rows = fall_samples()
            self.inject_fall = False
            print("[fake] injecting a fall-shaped motion window")
        else:
            maker = walking_sample if self.a.walking else still_sample
            step = 1.0 / MOTION_SAMPLE_RATE_HZ
            rows = [maker(t + i * step) for i in range(int(MOTION_HOP_S * MOTION_SAMPLE_RATE_HZ))]
        self.motion_buf.extend(rows)

    def publish_motion(self):
        """Publishes a full window, oldest first. See docs/mqtt-contract.md 3.5."""
        if len(self.motion_buf) < MOTION_WINDOW_SIZE:
            return
        self.motion_seq += 1
        self.publish(
            "motion",
            {
                "device_id": self.dev,
                "seq": self.motion_seq,
                "ts": now_iso(),
                "t0_ms": max(0, self.uptime_ms() - int((MOTION_WINDOW_SIZE - 1) * 100)),
                "sample_rate_hz": MOTION_SAMPLE_RATE_HZ,
                "window_size": MOTION_WINDOW_SIZE,
                "dropped": 0,
                "sim": True,
                "s": list(self.motion_buf),
            },
        )
        print(f"[fake] -> motion window #{self.motion_seq}")

    def raise_alert(self, alert_type, peak_g):
        self.event_seq += 1
        eid = f"{self.dev}-{self.boot_id}-{self.event_seq}"
        payload = {"device_id": self.dev, "event_id": eid, "ts": now_iso(), "uptime_ms": self.uptime_ms(),
                   "alert_type": alert_type, "status": "unresolved", "attempt": 1,
                   "accel_peak_g": peak_g, "vitals": self.vitals()}
        with self.lock:
            self.pending[eid] = {"payload": payload, "attempts": 0, "last": 0.0}
        print(f"[fake] ALERT {alert_type} raised ({eid})")

    def service_alerts(self):
        now = time.monotonic()
        with self.lock:
            for eid, p in list(self.pending.items()):
                if p["attempts"] > 0 and now - p["last"] < ALERT_RESEND_S:
                    continue
                p["payload"]["attempt"] = p["attempts"] + 1
                self.publish("event", p["payload"])
                p["attempts"] += 1
                p["last"] = now
                print(f"[fake] -> event {eid} attempt {p['attempts']}")
                if p["attempts"] >= ALERT_MAX_ATTEMPTS:
                    print(f"[fake] {eid}: no ack after {ALERT_MAX_ATTEMPTS} sends, giving up")
                    del self.pending[eid]

    # --- main loop ----------------------------------------------------------
    def run(self):
        self.client.connect(self.a.host, self.a.port, keepalive=15)
        self.client.loop_start()
        if not self.connected.wait(10):
            raise SystemExit("[fake] could not connect to the broker")
        sent = 0
        next_tel = time.monotonic()
        next_motion = time.monotonic()
        try:
            while self.a.count == 0 or sent < self.a.count or self.pending:
                now = time.monotonic()
                if (self.a.count == 0 or sent < self.a.count) and now >= next_tel:
                    fall = self.a.fall_at and sent == self.a.fall_at
                    self.publish_telemetry(peak_g=3.1 if fall else 1.0)
                    sent += 1
                    if self.a.sos_at and sent == self.a.sos_at:
                        self.raise_alert("manual_sos", 1.0)
                    if fall:
                        # Two layers, exactly as the firmware does it: the device
                        # rule fires immediately, and the next motion window
                        # carries the fall for the classifier to score.
                        self.raise_alert("fall_detected", 3.1)
                        self.inject_fall = True
                    next_tel = now + self.interval
                if self.motion_enabled and now >= next_motion:
                    self.fill_motion()
                    self.publish_motion()
                    next_motion = now + MOTION_HOP_S
                self.service_alerts()
                time.sleep(0.05)
        except KeyboardInterrupt:
            pass
        finally:
            # Graceful goodbye: publish offline ourselves (the Last Will is only for crashes).
            self.client.publish(topic(self.dev, "status"),
                                json.dumps({"device_id": self.dev, "state": "offline"}), qos=1, retain=True).wait_for_publish(5)
            self.client.loop_stop()
            self.client.disconnect()
        return {"telemetry": self.seq, "acked": self.acked}


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description="Fake JagSi watch")
    ap.add_argument("--host", default="broker.hivemq.com")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--device-id", default=f"jagsi-fake-{os.getpid() % 1000:03d}")
    ap.add_argument("--interval", type=float, default=2.0, help="seconds between telemetry")
    ap.add_argument("--count", type=int, default=0, help="telemetry messages to send (0 = forever)")
    ap.add_argument("--sos-at", type=int, default=0, help="press SOS after this telemetry number")
    ap.add_argument("--fall-at", type=int, default=0, help="simulate a fall after this telemetry number")
    ap.add_argument("--no-motion", action="store_true",
                    help="do not publish motion windows (telemetry and events only)")
    ap.add_argument("--walking", action="store_true",
                    help="generate gait motion instead of someone sitting still")
    return ap.parse_args(argv)


if __name__ == "__main__":
    FakeDevice(parse_args()).run()
