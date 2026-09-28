"""End-to-end test: fake device -> local mosquitto broker -> monitor (with auto-ack)."""
import pathlib
import shutil
import socket
import subprocess
import sys
import threading
import time

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import fake_device  # noqa: E402
import mqtt_monitor  # noqa: E402

MOSQUITTO = shutil.which("mosquitto") or ("/usr/sbin/mosquitto" if pathlib.Path("/usr/sbin/mosquitto").exists() else None)


@pytest.fixture
def broker_port():
    if not MOSQUITTO:
        pytest.skip("mosquitto not installed")
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen([MOSQUITTO, "-p", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.1)
    yield port
    proc.terminate()
    proc.wait(5)


def test_telemetry_and_alert_ack(broker_port, tmp_path):
    mon = mqtt_monitor.Monitor(mqtt_monitor.parse_args(
        ["--host", "127.0.0.1", "--port", str(broker_port), "--ack",
         "--csv-dir", str(tmp_path), "--seconds", "8"]))
    result = {}
    t = threading.Thread(target=lambda: result.update(mon.run()))
    t.start()
    time.sleep(1)  # let the monitor subscribe first

    dev = fake_device.FakeDevice(fake_device.parse_args(
        ["--host", "127.0.0.1", "--port", str(broker_port), "--device-id", "jagsi-test-01",
         "--interval", "0.5", "--count", "6", "--sos-at", "2", "--fall-at", "4"]))
    out = dev.run()
    t.join()

    assert out["telemetry"] == 6
    assert len(out["acked"]) == 2, "both alerts (SOS + fall) must be acknowledged"
    assert result["telemetry"] == 6
    assert result["event"] == 2          # acked on the first send -> no re-sends
    assert result["invalid"] == 0
    assert result["status"] >= 2         # online + offline

    tel_rows = (tmp_path / "telemetry.csv").read_text().strip().splitlines()
    evt_rows = (tmp_path / "events.csv").read_text().strip().splitlines()
    assert len(tel_rows) == 1 + 6
    assert len(evt_rows) == 1 + 2
    assert "manual_sos" in evt_rows[1] and "fall_detected" in evt_rows[2]


def test_alert_is_resent_without_ack(broker_port):
    """No monitor running -> the device must re-send the event up to 5 times."""
    import paho.mqtt.client as mqtt
    events = []
    sub = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    sub.on_message = lambda c, u, m: events.append(m.payload)
    sub.connect("127.0.0.1", broker_port)
    sub.subscribe("jagsi/abal/v1/jagsi-test-02/event")
    sub.loop_start()
    time.sleep(0.5)

    fake_device.ALERT_RESEND_S = 0.3   # speed up the test
    dev = fake_device.FakeDevice(fake_device.parse_args(
        ["--host", "127.0.0.1", "--port", str(broker_port), "--device-id", "jagsi-test-02",
         "--interval", "0.2", "--count", "1", "--sos-at", "1"]))
    dev.run()
    time.sleep(0.5)
    sub.loop_stop()
    assert len(events) == fake_device.ALERT_MAX_ATTEMPTS
