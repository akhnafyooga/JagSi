#!/usr/bin/env python3
"""End-to-end check of the issue #21 cloud path, timed like the real demo.

    fake watch -> MQTT -> Bridge -> SQLite -> mirror worker (python -m demo.cloud)
               -> PostgreSQL -> GET /api/devices/{id}/progress -> trend model

It publishes one telemetry reading every 2 seconds, as sketch.ino does, so a
full 60-reading window takes about two minutes. On the way it cuts the cloud
link, restarts the worker, acknowledges an SOS and lets the feed go stale.

Run from backend/. Against a disposable local PostgreSQL (what CI does):

    JAGSI_TEST_PG_DSN=postgresql://postgres:postgres@127.0.0.1:5432/postgres \\
        python scripts/cloud_check.py

Against the team's Supabase project, to produce demo evidence. It writes under a
fresh random source ID, so it never touches the real demo's rows:

    python scripts/cloud_check.py --supabase      (reads JAGSI_CLOUD_DSN from .env.demo)

Exit code 0 means every check passed.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(Path(__file__).resolve().parent))

TMP = Path(tempfile.mkdtemp(prefix="jagsi-cloud-check-"))
DEVICE = "jagsi-watch-01"
TOPIC_BASE = f"jagsi/abal/check-{uuid.uuid4().hex[:8]}/v1/"
SOURCE = str(uuid.uuid4())

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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--supabase", action="store_true",
                        help="use JAGSI_CLOUD_DSN from backend/.env.demo instead of JAGSI_TEST_PG_DSN")
    args = parser.parse_args()

    if args.supabase:
        from dotenv import dotenv_values

        dsn = dotenv_values(BACKEND / ".env.demo").get("JAGSI_CLOUD_DSN") or os.getenv("JAGSI_CLOUD_DSN", "")
        target = "Supabase (JAGSI_CLOUD_DSN)"
    else:
        dsn = os.getenv("JAGSI_TEST_PG_DSN", "")
        target = "local PostgreSQL (JAGSI_TEST_PG_DSN)"
    if not dsn:
        print("No database URI. Set JAGSI_TEST_PG_DSN, or use --supabase with backend/.env.demo.")
        return 2

    os.environ.update({
        "JAGSI_SKIP_ENV_FILE": "1",
        "JAGSI_CLOUD_DSN": dsn,
        "JAGSI_SOURCE_ID": SOURCE,
        "JAGSI_DEVICE_ID": DEVICE,
        "JAGSI_DB_PATH": str(TMP / "jagsi.db"),
        "JAGSI_TREND_MODEL": str(TMP / "trend_model.joblib"),
        "JAGSI_TOPIC_BASE": TOPIC_BASE,
        "JAGSI_RESTRICT_DEVICE": "true",
    })

    import paho.mqtt.client as mqtt
    import psycopg
    from fastapi.testclient import TestClient

    from integration_check import LocalBroker, free_port, wait_until

    from app.bridge import Bridge
    from app.config import Settings
    from app.store import Store
    from demo.train_trends import train

    print(f"\nJagSi cloud check: {target}, source {SOURCE}\n")
    print("0. Setup")
    with open(os.devnull, "w") as quiet:
        stdout, sys.stdout = sys.stdout, quiet
        try:
            train(TMP)
        finally:
            sys.stdout = stdout
    check("trend model trained from the #20 reference script", (TMP / "trend_model.joblib").exists())

    with psycopg.connect(dsn, autocommit=True, prepare_threshold=None) as conn:
        if not args.supabase:
            for role in ("anon", "authenticated"):
                conn.execute(f"do $$ begin create role {role} nologin; "
                             f"exception when duplicate_object then null; end $$")
        conn.execute((BACKEND / "demo" / "schema.sql").read_text())
    check("schema.sql applied (idempotent)", True)

    def cloud_count(kind: str) -> int:
        with psycopg.connect(dsn, prepare_threshold=None) as conn:
            return conn.execute(
                "select count(*) from public.jagsi_demo_records where source_id=%s and kind=%s",
                (SOURCE, kind)).fetchone()[0]

    def cloud_alert(alert_id: str):
        with psycopg.connect(dsn, prepare_threshold=None) as conn:
            row = conn.execute(
                "select payload from public.jagsi_demo_records "
                "where source_id=%s and kind='alert' and record_id=%s", (SOURCE, alert_id)).fetchone()
            return row[0] if row else None

    port = free_port()
    LocalBroker(port).start()
    settings = Settings(mqtt_host="127.0.0.1", mqtt_port=port, db_path=os.environ["JAGSI_DB_PATH"],
                        topic_base=TOPIC_BASE, device_id=DEVICE, restrict_device=True,
                        enable_classifier=False)
    store = Store(settings.db_path)
    bridge = Bridge(settings, store)
    bridge.start()
    check("bridge connected to the MQTT broker", wait_until(lambda: bridge.stats["connected"], 15))

    watch = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="cloud-check-watch")
    watch.connect("127.0.0.1", port)
    watch.loop_start()

    def publish(suffix: str, payload: dict) -> None:
        watch.publish(f"{TOPIC_BASE}{payload['device_id']}/{suffix}", json.dumps(payload))

    seq = {"n": 0}

    def reading(hr: float) -> None:
        seq["n"] += 1
        publish("telemetry", {
            "device_id": DEVICE, "seq": seq["n"], "ts": None, "uptime_ms": 2000 * seq["n"],
            "heart_rate": round(hr), "spo2": 98.0, "body_temperature": 36.6,
            "accel": {"x": 0.0, "y": 0.0, "z": 1.0}, "accel_peak_g": 1.0,
            "battery_level": 90, "sim": True})

    env = {**os.environ, "PYTHONPATH": str(BACKEND)}
    log_path = TMP / "worker.log"

    def start_worker():
        return subprocess.Popen([sys.executable, "-m", "demo.cloud"], cwd=BACKEND, env=env,
                                stdout=open(log_path, "a"), stderr=subprocess.STDOUT)

    worker = start_worker()
    from app.main import app

    api = TestClient(app)

    # 1. readings flow into the cloud ------------------------------------------
    print("\n1. Telemetry reaches the cloud (R07)")
    publish("telemetry", {"device_id": "intruder", "seq": 1, "heart_rate": 200})
    for i in range(5):
        reading(75)
        time.sleep(2)
    check("5 readings mirrored within 5 s of arrival",
          wait_until(lambda: cloud_count("telemetry") == 5, 5), f"cloud has {cloud_count('telemetry')}")
    check("message with mismatched device_id was rejected, not stored",
          bridge.stats["messages_rejected"] >= 1 and cloud_count("telemetry") == 5)
    early = api.get(f"/api/devices/{DEVICE}/progress").json()
    check("progress says insufficient_data before 60 readings",
          early.get("state") == "insufficient_data", str(early))

    # 2. cloud outage ------------------------------------------------------------
    print("\n2. Cloud outage and catch-up (R08)")
    worker.terminate()
    worker.wait(10)
    before = cloud_count("telemetry")
    for i in range(10):
        reading(75 + i * 0.4)
        time.sleep(2)
    check("SQLite kept collecting while the mirror was down",
          len(store.telemetry_history(DEVICE, 100)) == 15 and cloud_count("telemetry") == before)
    worker = start_worker()
    check("restarted worker caught up the 10-row backlog",
          wait_until(lambda: cloud_count("telemetry") == 15, 10), f"cloud has {cloud_count('telemetry')}")

    # 3. SOS acknowledgment ----------------------------------------------------------
    print("\n3. Alert snapshot follows the acknowledgment")
    publish("event", {"device_id": DEVICE, "event_id": "sos-check-1", "ts": None, "uptime_ms": 1,
                      "alert_type": "manual_sos", "status": "unresolved", "attempt": 1,
                      "accel_peak_g": 1.0, "vitals": {"heart_rate": 80}})
    reading(80)
    time.sleep(2)
    check("SOS stored in the cloud as unresolved",
          wait_until(lambda: (cloud_alert("sos-check-1") or {}).get("status") == "unresolved", 6))
    store.acknowledge_alert("sos-check-1")
    check("caregiver acknowledgment reached the cloud",
          wait_until(lambda: (cloud_alert("sos-check-1") or {}).get("status") == "acknowledged", 6))

    # 4. a full window with a rising heart rate ------------------------------------
    print("\n4. Trend inference on 60 stored readings (R09), about 90 s")
    target = 60 - seq["n"]
    for i in range(target):
        reading(81 + 25 * (i + 1) / target)
        time.sleep(2)
    wait_until(lambda: cloud_count("telemetry") >= 60, 6)
    started = time.time()
    response = api.get(f"/api/devices/{DEVICE}/progress")
    elapsed_ms = (time.time() - started) * 1000
    body = response.json()
    print("        " + json.dumps({k: body.get(k) for k in
                                   ("state", "label", "confidence", "model_version",
                                    "telemetry_ids", "span_seconds", "guidance")}, ensure_ascii=False))
    check("progress returned a ready prediction", body.get("state") == "ready", str(body)[:300])
    check("pattern recognised as rising_hr", body.get("label") == "rising_hr", body.get("label", ""))
    check("result traces back to stored telemetry IDs",
          isinstance(body.get("telemetry_ids"), list) and len(body["telemetry_ids"]) == 2)
    check("analysis row stored in the cloud", cloud_count("analysis") == 1)
    check(f"progress answered in {elapsed_ms:.0f} ms", elapsed_ms < 5000)
    history = api.get(f"/api/devices/{DEVICE}/cloud-history").json()
    ids = [p["telemetry_id"] for p in history.get("points", [])]
    check("cloud history is oldest-first and complete", ids == sorted(ids) and len(ids) == 60)

    # 5. restart, no duplicates -----------------------------------------------------
    print("\n5. Restart and replay")
    worker.terminate()
    worker.wait(10)
    counts = (cloud_count("telemetry"), cloud_count("alert"))
    worker = start_worker()
    time.sleep(4)
    check("restart with the same source ID added no duplicates",
          (cloud_count("telemetry"), cloud_count("alert")) == counts, f"{counts}")

    # 6. the feed stops ---------------------------------------------------------------
    print("\n6. Stale feed")
    time.sleep(11)
    stale = api.get(f"/api/devices/{DEVICE}/progress").json()
    check("no prediction once readings are older than 10 s", stale.get("state") == "stale", str(stale))

    worker.terminate()
    worker.wait(10)
    bridge.stop()
    watch.loop_stop()
    log_text = log_path.read_text()
    check("worker log shows mirrored batches and no failures",
          "mirrored telemetry=" in log_text and "sync failed" not in log_text)
    check("database URI never printed by the worker", dsn not in log_text)

    print(f"\n{passed + failed} checks, {passed} passed, {failed} failed")
    print(f"worker log: {log_path}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
