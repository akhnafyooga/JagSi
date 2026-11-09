#!/usr/bin/env python3
"""Whole-pipeline check for the Azure transport (issue #8), no Azure account.

The Week 6 counterpart, scripts/integration_check.py, runs a local MQTT broker.
This one replays what Azure would send instead: Event Grid deliveries, built from
the documented event schema, carrying payloads shaped exactly like the firmware's.
They go through the real FastAPI webhook, the real Bridge, the real classifier and
the real SQLite store. Only the HTTPS call to IoT Hub for direct methods is
replaced, by a recorder, so the acks the backend would send can be checked.

    cd backend && python3 scripts/eventgrid_check.py
"""

from __future__ import annotations

import os
import sys
import tempfile
import warnings
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND.parent / "tools"))
warnings.filterwarnings("ignore")

_TMP = Path(tempfile.mkdtemp(prefix="jagsi-eg-"))
os.environ.update(
    {
        "JAGSI_DB_PATH": str(_TMP / "eg.db"),
        "JAGSI_INGEST": "azure",
        "JAGSI_IOTHUB_HOSTNAME": "jagsi-check.azure-devices.net",
        "JAGSI_IOTHUB_POLICY_KEY": "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        "JAGSI_EVENTGRID_KEY": "check-key",
        "JAGSI_FALL_THRESHOLD": "0.30",
        "JAGSI_RECORDINGS_DIR": str(_TMP / "rec"),
    }
)
os.environ.pop("GEMINI_API_KEY", None)

import random  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from fake_device import MOTION_WINDOW_SIZE, fall_samples, walking_sample  # noqa: E402

from app import main  # noqa: E402

DEV = "jagsi-watch-01"
URL = "/api/ingest/eventgrid?key=check-key"


class AckRecorder:
    """Stands in for DirectMethodSender: records instead of calling IoT Hub."""

    def __init__(self):
        self.sent = []

    def invoke(self, device_id, command):
        self.sent.append((device_id, command))
        return True

    invoke_background = invoke

    def close(self):
        pass


def telemetry_event(body, kind, device=DEV):
    return {
        "id": f"{kind}-{random.getrandbits(32):08x}",
        "eventType": "Microsoft.Devices.DeviceTelemetry",
        "subject": f"devices/{device}",
        "data": {
            "body": body,
            "properties": {"type": kind},
            "systemProperties": {
                "iothub-content-type": "application/json",
                "iothub-content-encoding": "utf-8",
                "iothub-connection-device-id": device,
            },
        },
    }


def motion(seq, rows):
    return {
        "device_id": DEV, "seq": seq, "ts": "2026-11-09T07:00:00Z", "t0_ms": seq * 1000,
        "sample_rate_hz": 10, "window_size": MOTION_WINDOW_SIZE, "dropped": 0, "sim": True, "s": rows,
    }


results = []


def check(name, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail and not ok else ""))


def run() -> int:
    random.seed(11)
    acks = AckRecorder()
    main.bridge.command_sender = acks
    main.bridge.load_classifier()
    client = TestClient(main.app)

    r = client.post(URL, json=[{"eventType": "Microsoft.EventGrid.SubscriptionValidationEvent", "data": {"validationCode": "v1"}}])
    check("Event Grid validation handshake echoes the code", r.json() == {"validationResponse": "v1"})
    check("wrong webhook key is refused", client.post("/api/ingest/eventgrid?key=x", json=[]).status_code == 401)

    client.post(URL, json=[{"eventType": "Microsoft.Devices.DeviceConnected", "data": {"deviceId": DEV}}])
    check("DeviceConnected marks the watch online", (main.store.device(DEV) or {}).get("state") == "online")

    status = {"device_id": DEV, "state": "online", "fw": "0.2.0", "battery_level": 87, "interval_ms": 2000, "motion_enabled": True}
    client.post(URL, json=[telemetry_event(status, "status")])
    check("status message stores firmware version", main.store.device(DEV)["fw"] == "0.2.0")

    for seq in (1, 2, 3):
        tel = {
            "device_id": DEV, "seq": seq, "ts": None, "uptime_ms": seq * 2000, "heart_rate": 76 + seq,
            "spo2": 97.2, "body_temperature": 36.6, "accel": {"x": 0, "y": 0, "z": 1},
            "gyro": {"x": 0, "y": 0, "z": 0}, "accel_peak_g": 1.0, "battery_level": 87, "sim": True,
        }
        client.post(URL, json=[telemetry_event(tel, "telemetry")])
    latest = main.store.latest_telemetry(DEV)
    check("telemetry stored, newest first", latest["seq"] == 3 and latest["heart_rate"] == 79)
    check("null device clock falls back to server time", latest["ts_source"] == "server")

    api = client.get(f"/api/devices/{DEV}/telemetry/latest").json()
    check("dashboard endpoint serves the IoT Hub data", api["device_id"] == DEV and len(api["vitals"]) == 4)

    walking = [motion(i, [walking_sample(i + k / 10) for k in range(MOTION_WINDOW_SIZE)]) for i in range(20)]
    client.post(URL, json=[telemetry_event(w, "motion") for w in walking])
    ml_alerts = [a for a in main.store.recent_alerts(device_id=DEV) if a["source"] == "ml"]
    check("20 walking windows scored, no false alert at threshold 0.30",
          main.bridge.stats["motion_scored"] == 20 and not ml_alerts,
          f"scored={main.bridge.stats['motion_scored']} alerts={len(ml_alerts)}")

    lead = [walking_sample(100 + k / 10) for k in range(MOTION_WINDOW_SIZE - 10)]
    client.post(URL, json=[telemetry_event(motion(100, lead + fall_samples()), "motion")])
    ml_alerts = [a for a in main.store.recent_alerts(device_id=DEV) if a["source"] == "ml"]
    check("a fall window raises one ML alert with its confidence",
          len(ml_alerts) == 1 and ml_alerts[0]["confidence"] > 0.3)

    bad = motion(101, [[0, 0, 1]] * MOTION_WINDOW_SIZE)
    client.post(URL, json=[telemetry_event(bad, "motion")])
    check("malformed window rejected, not scored", main.bridge.stats["motion_rejected"] == 1)

    sos = {"device_id": DEV, "event_id": f"{DEV}-cafe0001-1", "ts": "2026-11-09T07:01:00Z",
           "alert_type": "manual_sos", "status": "unresolved", "attempt": 1}
    client.post(URL, json=[telemetry_event(sos, "event")])
    client.post(URL, json=[telemetry_event({**sos, "attempt": 2}, "event")])
    sos_rows = [a for a in main.store.recent_alerts(device_id=DEV) if a["alert_id"] == sos["event_id"]]
    check("SOS stored once even when the watch re-sends it", len(sos_rows) == 1)
    ack = (DEV, {"cmd": "ack_alert", "event_id": sos["event_id"]})
    check("every SOS delivery is acked by direct method", acks.sent.count(ack) == 2)

    spoof = telemetry_event({"device_id": "jagsi-watch-99", "heart_rate": 40}, "telemetry", device=DEV)
    r = client.post(URL, json=[spoof])
    check("payload claiming another device is refused", r.status_code == 400 and main.store.latest_telemetry("jagsi-watch-99") is None)

    r = client.post(f"/api/devices/{DEV}/command", json={"cmd": "set_motion", "enabled": False})
    check("dashboard command goes out as a direct method",
          r.status_code == 200 and (DEV, {"cmd": "set_motion", "enabled": False}) in acks.sent)

    summary = client.get(f"/api/devices/{DEV}/summary").json()
    check("AI summary mentions the open alerts first (rules, no key)",
          summary["source"] == "rules" and summary["text"].startswith("Ada "), summary["text"][:60])

    client.post(URL, json=[{"eventType": "Microsoft.Devices.DeviceDisconnected", "data": {"deviceId": DEV}}])
    dev = main.store.device(DEV)
    check("DeviceDisconnected marks offline and keeps known fields", dev["state"] == "offline" and dev["fw"] == "0.2.0")

    health = client.get("/api/health").json()
    check("health reports azure ingest and no MQTT topics", health["ingest"] == "azure" and health["subscribed_to"] == [])

    passed = sum(results)
    print(f"\n{len(results)} checks, {passed} passed, {len(results) - passed} failed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(run())
