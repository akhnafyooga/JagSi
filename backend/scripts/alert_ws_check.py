#!/usr/bin/env python3
"""End-to-end check of real-time emergency notifications (issue #13).

Runs the real backend (uvicorn, as a separate process) against a throwaway MQTT
broker, plays the watch with payloads byte-identical to sketch.ino, and listens
the way the dashboard does, on /ws/alerts:

    watch --MQTT--> broker --> Bridge --> SQLite --> Hub --> /ws/alerts --> dashboard
                                                                 |
    watch <--MQTT cmd ack_alert-- Bridge <-- "Saya tangani" -----+

It measures how long an SOS takes from the watch to the dashboard, and checks
that an acknowledgement from one caregiver closes the alert everywhere and
reaches the watch.

Run from backend/:

    pip install amqtt
    python3 scripts/alert_ws_check.py

Exit code 0 means every check passed.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import paho.mqtt.client as mqtt  # noqa: E402
from websockets.exceptions import InvalidStatus  # noqa: E402
from websockets.sync.client import connect  # noqa: E402

from integration_check import (  # noqa: E402  (same broker and payloads as Week 6)
    DEVICE,
    TOPIC_BASE,
    LocalBroker,
    event_payload,
    fall_rows,
    free_port,
    motion_payload,
    status_payload,
    telemetry_payload,
    wait_until,
)

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


def http(method: str, url: str) -> dict:
    req = urllib.request.Request(url, method=method, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def next_of(ws, kind: str, timeout: float = 5.0) -> dict | None:
    """Reads past pings and other events until ``kind`` arrives, or None on timeout."""
    deadline = time.monotonic() + timeout
    while True:
        left = deadline - time.monotonic()
        if left <= 0:
            return None
        try:
            msg = json.loads(ws.recv(timeout=left))
        except TimeoutError:
            return None
        if msg.get("type") == kind:
            return msg


def main() -> int:
    mqtt_port = free_port()
    api_port = free_port()
    api = f"http://127.0.0.1:{api_port}"
    ws_url = f"ws://127.0.0.1:{api_port}/ws/alerts"
    origin = "http://localhost:3000"
    print(f"\nJagSi real-time alert check (broker :{mqtt_port}, API :{api_port})\n")

    broker = LocalBroker(mqtt_port)
    broker.start()

    tmp = Path(tempfile.mkdtemp(prefix="jagsi-alert-check-"))
    env = {
        **os.environ,
        "JAGSI_INGEST": "mqtt",
        "JAGSI_MQTT_HOST": "127.0.0.1",
        "JAGSI_MQTT_PORT": str(mqtt_port),
        "JAGSI_DB_PATH": str(tmp / "alerts.db"),
        "JAGSI_RECORDINGS_DIR": str(tmp / "rec"),
        "JAGSI_CORS_ORIGINS": origin,
        "JAGSI_DUPLICATE_WINDOW_S": "0",
        "JAGSI_ML_COOLDOWN_S": "0",
    }
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", str(api_port), "--log-level", "warning"],
        cwd=HERE.parent,
        env=env,
    )
    device = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="fake-watch-ws-check")
    try:
        def bridge_connected() -> bool:
            try:
                return bool(http("GET", f"{api}/api/health")["bridge"].get("connected"))
            except Exception:
                return False

        check("backend started and bridge connected to the broker", wait_until(bridge_connected, timeout=30))

        commands: list[dict] = []
        device.on_message = lambda c, u, m: commands.append(json.loads(m.payload))
        device.connect("127.0.0.1", mqtt_port)
        device.loop_start()
        device.subscribe(f"{TOPIC_BASE}{DEVICE}/cmd", qos=1)
        time.sleep(0.5)

        def publish(suffix: str, payload: dict) -> None:
            device.publish(f"{TOPIC_BASE}{DEVICE}/{suffix}", json.dumps(payload), qos=1).wait_for_publish(5)

        publish("status", status_payload())
        publish("telemetry", telemetry_payload(1, 36.6))

        # 1. Origin check: a random website must not be able to open the socket.
        try:
            with connect(ws_url, origin="https://evil.example", open_timeout=5):
                refused = False
        except InvalidStatus as exc:
            refused = exc.response.status_code == 403
        check("socket refuses a page from another origin (HTTP 403)", refused)

        with connect(ws_url, origin=origin) as a, connect(ws_url, origin=origin) as b:
            hello = next_of(a, "hello")
            next_of(b, "hello")
            check("dashboard receives the hello snapshot", hello is not None and hello["data"]["open_alerts"] == [])

            # 2. SOS from the watch, timed to the dashboard. Five rounds.
            latencies = []
            for i in range(5):
                event_id = f"sos-check-{i}"
                payload = {**event_payload(event_id), "alert_type": "manual_sos"}
                t0 = time.monotonic()
                publish("event", payload)
                got = next_of(a, "alert")
                if got is None or got["data"]["alert_id"] != event_id:
                    check(f"SOS {i} reaches the dashboard", False, repr(got))
                    break
                latencies.append((time.monotonic() - t0) * 1000)
                next_of(b, "alert")
                a.send(json.dumps({"type": "ack", "alert_id": event_id}))
                next_of(a, "ack_result")
                next_of(b, "alert_ack")
            if len(latencies) == 5:
                check(
                    f"5/5 SOS presses reached the dashboard (median {statistics.median(latencies):.0f} ms, "
                    f"max {max(latencies):.0f} ms)",
                    max(latencies) < 1000,
                    f"latencies {latencies}",
                )

            # 3. A fall with vitals; caregiver A handles it, B's screen closes.
            publish("event", event_payload("fall-check-1"))
            alert = next_of(a, "alert")
            next_of(b, "alert")
            check(
                "fall alert carries the vitals as an object",
                alert is not None and alert["data"]["vitals"] == {"heart_rate": 102, "spo2": 94.0, "body_temperature": 37.1},
                repr(alert),
            )
            commands.clear()
            a.send(json.dumps({"type": "ack", "alert_id": "fall-check-1"}))
            result = next_of(a, "ack_result")
            closed_on_b = next_of(b, "alert_ack")
            check("caregiver A gets ack_result", result is not None and result["data"]["status"] == "acknowledged")
            check(
                "caregiver B's screen closes (alert_ack via websocket)",
                closed_on_b is not None and closed_on_b["data"]["via"] == "websocket",
            )
            check(
                "the watch receives ack_alert on its cmd topic",
                wait_until(lambda: {"cmd": "ack_alert", "event_id": "fall-check-1"} in commands, timeout=5),
                repr(commands),
            )
            stored = http("GET", f"{api}/api/alerts?limit=50")["alerts"]
            check(
                "alert is stored as acknowledged",
                any(x["alert_id"] == "fall-check-1" and x["status"] == "acknowledged" for x in stored),
            )

            # 4. ML alert from a motion window, acknowledged through the REST API.
            publish("motion", motion_payload(10, fall_rows()))
            ml = next_of(a, "alert", timeout=10)
            next_of(b, "alert")
            check("ML fall detection is pushed to the socket", ml is not None and ml["data"]["source"] == "ml", repr(ml))
            if ml is not None:
                t0 = time.monotonic()
                http("POST", f"{api}/api/alerts/{ml['data']['alert_id']}/ack")
                heard = next_of(a, "alert_ack", timeout=5)
                elapsed = (time.monotonic() - t0) * 1000
                check(
                    f"ack from the REST API reaches the socket in {elapsed:.0f} ms",
                    heard is not None and elapsed < 1000,
                )

            # 5. An alert that fires while the dashboard is away is not lost.
            publish("event", {**event_payload("while-away"), "alert_type": "manual_sos"})
            next_of(a, "alert")

        time.sleep(0.3)
        with connect(ws_url, origin=origin) as c:
            hello = next_of(c, "hello")
            open_ids = [x["alert_id"] for x in hello["data"]["open_alerts"]] if hello else []
            check("a dashboard that reconnects still sees the open alert", open_ids == ["while-away"], repr(open_ids))

            c.send(json.dumps({"type": "ping"}))
            check("ping is answered with pong", next_of(c, "pong") is not None)
    finally:
        device.loop_stop()
        device.disconnect()
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()

    print(f"\n{passed} checks, {passed} passed, {failed} failed\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
