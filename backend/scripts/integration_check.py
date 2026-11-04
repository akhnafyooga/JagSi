#!/usr/bin/env python3
"""End-to-end check of the JagSi pipeline, without a device and without the cloud.

Starts a throwaway MQTT broker on localhost, runs the real Bridge against it,
publishes payloads byte-identical to what sketch.ino emits, and then asserts that
the database and the classifier did what docs/mqtt-contract.md says they should.

It covers the whole chain apart from the ESP32 itself:

    fake device -> MQTT -> Bridge -> validation -> SQLite
                                  -> FallClassifier -> ALERT_EVENT

Run from the backend/ directory:

    python3 scripts/integration_check.py

Exit code 0 means every step passed. Use it as the repeatable evidence for the
pipeline instead of a Wokwi screenshot, which proves only that the device talks.
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paho.mqtt.client as mqtt  # noqa: E402
from amqtt.broker import Broker  # noqa: E402

from app.bridge import Bridge  # noqa: E402
from app.config import Settings  # noqa: E402
from app.store import Store  # noqa: E402

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s %(message)s")

DEVICE = "jagsi-watch-01"
TOPIC_BASE = "jagsi/abal/v1/"

passed = 0
failed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {label}")
    else:
        failed += 1
        print(f"  FAIL  {label}" + (f"  -> {detail}" if detail else ""))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# --------------------------------------------------------------------------
# Payload builders: these mirror sketch.ino exactly. If the firmware payload
# changes, change it here too and the mismatch shows up as a failure.
# --------------------------------------------------------------------------
def telemetry_payload(seq: int, temp_c: float) -> dict:
    return {
        "device_id": DEVICE,
        "seq": seq,
        "ts": None,                      # NTP not synced yet, the common case on boot
        "uptime_ms": 1000 * seq,
        "heart_rate": 78,
        "spo2": 97.0,
        "body_temperature": temp_c,
        "accel": {"x": 0.0, "y": 0.0, "z": 1.0},
        "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
        "accel_peak_g": 1.0,
        "battery_level": 87,
        "sim": True,
    }


def motion_payload(seq: int, rows: list, dropped: int = 0) -> dict:
    return {
        "device_id": DEVICE,
        "seq": seq,
        "ts": "2026-11-04T12:00:03Z",
        "t0_ms": 84000,
        "sample_rate_hz": 10,
        "window_size": 30,
        "dropped": dropped,
        "sim": True,
        "s": rows,
    }


def still_rows() -> list:
    return [[0.01, 0.01, 1.0, 0.2, 0.1, 0.05] for _ in range(30)]


def fall_rows() -> list:
    """Upright, free fall, impact spike, then lying still."""
    rows = [[0.05, 0.05, 1.0, 2.0, 1.0, 0.5] for _ in range(8)]
    rows += [[0.05, 0.05, 0.15, 30.0, 20.0, 10.0] for _ in range(4)]
    rows.append([1.2, 1.5, 2.6, 250.0, 180.0, 120.0])
    rows.append([0.6, 0.7, 1.4, 90.0, 60.0, 40.0])
    rows += [[0.95, 0.1, 0.08, 0.5, 0.3, 0.2] for _ in range(30 - len(rows))]
    return rows[:30]


def status_payload(state: str = "online") -> dict:
    return {
        "device_id": DEVICE,
        "state": state,
        "fw": "0.1.0",
        "battery_level": 87,
        "rssi": -60,
        "ip": "10.10.0.2",
        "interval_ms": 2000,
        "motion_enabled": True,
        "sample_rate_hz": 10,
    }


def event_payload(event_id: str, attempt: int = 1) -> dict:
    return {
        "device_id": DEVICE,
        "event_id": event_id,
        "ts": "2026-11-04T12:00:05Z",
        "uptime_ms": 89000,
        "alert_type": "fall_detected",
        "status": "unresolved",
        "attempt": attempt,
        "accel_peak_g": 2.8,
        "vitals": {"heart_rate": 102, "spo2": 94.0, "body_temperature": 37.1},
    }


# --------------------------------------------------------------------------
# Throwaway broker
# --------------------------------------------------------------------------
class LocalBroker:
    def __init__(self, port: int) -> None:
        self.port = port
        self._loop: asyncio.AbstractEventLoop | None = None
        self._broker: Broker | None = None
        self._ready = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        config = {
            "listeners": {"default": {"type": "tcp", "bind": f"127.0.0.1:{self.port}"}},
            "sys_interval": 0,
            "auth": {"allow-anonymous": True, "plugins": ["auth_anonymous"]},
            "topic-check": {"enabled": False},
        }
        async def main():
            # Broker() must be constructed inside the running loop: it calls
            # asyncio.get_running_loop() in __init__.
            self._broker = Broker(config)
            await self._broker.start()
            self._ready.set()
            while True:
                await asyncio.sleep(3600)

        try:
            self._loop.run_until_complete(main())
        except Exception:
            self._ready.set()

    def start(self, timeout: float = 15.0) -> None:
        self._thread.start()
        if not self._ready.wait(timeout):
            raise RuntimeError("local broker did not start")
        time.sleep(0.5)


def wait_until(predicate, timeout: float = 10.0, interval: float = 0.1) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def main() -> int:
    port = free_port()
    print(f"\nJagSi pipeline integration check (broker on 127.0.0.1:{port})\n")

    broker = LocalBroker(port)
    broker.start()

    tmp = Path(tempfile.mkdtemp(prefix="jagsi-integration-"))
    settings = Settings(
        mqtt_host="127.0.0.1",
        mqtt_port=port,
        db_path=str(tmp / "jagsi.db"),
        topic_base=TOPIC_BASE,
        device_id=DEVICE,
    )
    store = Store(settings.db_path)

    # Capture what the dashboard would receive over SSE.
    sse_events: list = []
    loop = asyncio.new_event_loop()
    threading.Thread(target=loop.run_forever, daemon=True).start()

    bridge = Bridge(settings, store, on_event=sse_events.append)
    bridge.attach_loop(loop)
    bridge.start()

    if not wait_until(lambda: bridge.stats["connected"], timeout=15):
        print("  FAIL  bridge could not connect to the local broker")
        return 1
    print("  PASS  bridge connected and subscribed")
    global passed
    passed += 1

    check(
        "fall classifier loaded",
        bridge.stats["classifier_loaded"],
        "running in store-only mode, ML steps will be skipped",
    )

    # The fake device.
    device = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fake-watch")
    acks: list = []
    device.on_message = lambda c, u, m: acks.append(json.loads(m.payload.decode()))
    device.connect("127.0.0.1", port, keepalive=30)
    device.loop_start()
    device.subscribe(f"{TOPIC_BASE}{DEVICE}/cmd", qos=1)
    time.sleep(0.4)

    def publish(suffix: str, payload: dict, retain: bool = False) -> None:
        device.publish(
            f"{TOPIC_BASE}{DEVICE}/{suffix}", json.dumps(payload), qos=0, retain=retain
        )

    # --- 1. status ---------------------------------------------------------
    print("\n1. Device status")
    publish("status", status_payload(), retain=True)
    check(
        "status stored in wearable_device",
        wait_until(lambda: (store.device(DEVICE) or {}).get("state") == "online"),
    )

    # --- 2. telemetry ------------------------------------------------------
    print("\n2. Telemetry to database")
    for i in range(1, 4):
        publish("telemetry", telemetry_payload(i, 36.4 + i / 10))
    check("three telemetry rows stored", wait_until(lambda: bridge.stats["telemetry"] >= 3))

    latest = store.latest_telemetry(DEVICE) or {}
    check(
        "newest temperature is the one just published",
        latest.get("body_temperature") is not None
        and abs(latest["body_temperature"] - 36.7) < 1e-6,
        f"got {latest.get('body_temperature')}",
    )
    check(
        "null device clock replaced by server time and flagged",
        latest.get("ts_source") == "server",
        f"ts_source={latest.get('ts_source')}",
    )
    check("telemetry pushed to the dashboard stream",
          any(e["type"] == "telemetry" for e in sse_events))

    # --- 3. motion windows -------------------------------------------------
    print("\n3. Motion windows to the classifier")
    if bridge.stats["classifier_loaded"]:
        publish("motion", motion_payload(1, still_rows()))
        check("still window scored", wait_until(lambda: bridge.stats["motion_scored"] >= 1))
        check(
            "still window raised no alert",
            bridge.stats["alerts_ml"] == 0,
            f"alerts_ml={bridge.stats['alerts_ml']}",
        )

        publish("motion", motion_payload(2, still_rows(), dropped=4))
        check(
            "window with dropped samples rejected, not scored",
            wait_until(lambda: bridge.stats["motion_rejected"] >= 1),
            bridge.stats["last_reject_reason"] or "",
        )

        publish("motion", motion_payload(3, [[0.0, 0.0, 1.0] for _ in range(30)]))
        check(
            "malformed row rejected",
            wait_until(lambda: bridge.stats["motion_rejected"] >= 2),
            bridge.stats["last_reject_reason"] or "",
        )

        publish("motion", motion_payload(4, fall_rows()))
        check("fall window raised an ML alert", wait_until(lambda: bridge.stats["alerts_ml"] >= 1))

        ml_alerts = [a for a in store.recent_alerts() if a["source"] == "ml"]
        check("ML alert recorded with source=ml", len(ml_alerts) == 1)
        if ml_alerts:
            confidence = ml_alerts[0]["confidence"]
            check(
                "ML alert carries a confidence",
                confidence is not None and 0.0 <= confidence <= 1.0,
                f"confidence={confidence}",
            )
            print(f"        confidence recorded: {confidence}")

        # --- 4. no alert storm from overlapping windows --------------------
        print("\n4. Overlapping windows must not alert repeatedly")
        before = bridge.stats["alerts_ml"]
        for seq in range(5, 8):
            publish("motion", motion_payload(seq, fall_rows()))
            time.sleep(0.3)
        time.sleep(1.0)
        check(
            "three more fall windows produced no extra alerts",
            bridge.stats["alerts_ml"] == before,
            f"alerts went from {before} to {bridge.stats['alerts_ml']}",
        )
    else:
        print("  SKIP  classifier not loaded")

    # --- 5. device event, dedup, and ack -----------------------------------
    print("\n5. Device-rule event, de-duplication and ack")
    publish("event", event_payload("evt-1", attempt=1))
    check("device event stored", wait_until(lambda: bridge.stats["alerts_device"] >= 1))
    check("ack_alert sent back to the device",
          wait_until(lambda: any(a.get("cmd") == "ack_alert" for a in acks)))

    for attempt in range(2, 6):
        publish("event", event_payload("evt-1", attempt=attempt))
    time.sleep(1.0)
    device_alerts = [a for a in store.recent_alerts(limit=50) if a["alert_id"] == "evt-1"]
    check("re-sent event did not create duplicates", len(device_alerts) == 1)
    check(
        "re-send attempts counted on the single row",
        device_alerts and device_alerts[0]["attempts"] == 5,
        f"attempts={device_alerts[0]['attempts'] if device_alerts else 'n/a'}",
    )
    check("alert pushed to the dashboard stream",
          any(e["type"] == "alert" for e in sse_events))

    # --- 6. offline will --------------------------------------------------
    print("\n6. Last Will keeps known device fields")
    publish("status", {"device_id": DEVICE, "state": "offline"})
    wait_until(lambda: (store.device(DEVICE) or {}).get("state") == "offline")
    device_row = store.device(DEVICE) or {}
    check("state became offline", device_row.get("state") == "offline")
    check(
        "firmware version was not wiped by the bare will payload",
        device_row.get("fw") == "0.1.0",
        f"fw={device_row.get('fw')}",
    )

    device.loop_stop()
    device.disconnect()
    bridge.stop()

    print("\n" + "-" * 68)
    print("bridge stats:", json.dumps(bridge.stats, indent=2, default=str))
    print(f"\n{passed + failed} checks, {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
