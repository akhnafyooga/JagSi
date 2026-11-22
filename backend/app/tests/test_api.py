"""API surface the dashboard calls.

TestClient is used without its context manager on purpose: entering it would run
the lifespan hook, which opens a real MQTT connection to the broker.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app, store

client = TestClient(app)

DEVICE = "jagsi-watch-01"


@pytest.fixture(autouse=True)
def seed():
    store.insert_telemetry(
        {
            "device_id": DEVICE,
            "seq": 1,
            "ts": "2026-11-04T12:00:00Z",
            "uptime_ms": 1000,
            "heart_rate": 78,
            "spo2": 97.0,
            "body_temperature": 36.6,
            "accel": {"x": 0.0, "y": 0.0, "z": 1.0},
            "accel_peak_g": 1.0,
            "battery_level": 87,
            "sim": True,
        }
    )
    store.upsert_device({"device_id": DEVICE, "state": "online", "fw": "0.1.0"})


def test_health_reports_bridge_state():
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert "bridge" in body
    assert any(t.endswith("/telemetry") for t in body["subscribed_to"])
    # The cmd topic must not be subscribed: the bridge publishes to it.
    assert not any(t.endswith("/cmd") for t in body["subscribed_to"])


def test_latest_telemetry_returns_dashboard_shaped_vitals():
    body = client.get(f"/api/devices/{DEVICE}/telemetry/latest").json()
    assert body["device_id"] == DEVICE
    assert body["simulated"] is True

    vitals = {v["id"]: v for v in body["vitals"]}
    assert set(vitals) == {"heart-rate", "spo2", "temperature", "battery"}
    assert vitals["temperature"]["value"] == 36.6
    assert vitals["temperature"]["tone"] == "normal"
    # DS18B20 is a real part in Wokwi; heart rate is a potentiometer.
    assert vitals["temperature"]["simulated"] is False
    assert vitals["heart-rate"]["simulated"] is True


def test_latest_telemetry_404_for_unknown_device():
    response = client.get("/api/devices/does-not-exist/telemetry/latest")
    assert response.status_code == 404
    assert "no telemetry stored" in response.json()["detail"]


def test_history_shape_and_limit_clamp():
    body = client.get(f"/api/devices/{DEVICE}/telemetry/history?limit=9999").json()
    assert body["count"] >= 1
    assert set(body["points"][0]) == {
        "received_at",
        "heart_rate",
        "spo2",
        "body_temperature",
        "accel_peak_g",
    }


def test_alerts_expose_vitals_as_json_not_a_string():
    store.insert_alert(
        alert_id="api-alert-1",
        device_id=DEVICE,
        alert_type="fall_detected",
        source="ml",
        confidence=0.87,
        vitals={"heart_rate": 102, "spo2": 94.0, "body_temperature": 37.1},
    )
    alerts = client.get("/api/alerts").json()["alerts"]
    alert = next(a for a in alerts if a["alert_id"] == "api-alert-1")
    assert alert["source"] == "ml"
    assert alert["confidence"] == 0.87
    assert alert["vitals"]["heart_rate"] == 102
    assert "vitals_json" not in alert


def test_acknowledging_an_ml_alert_does_not_require_the_broker():
    store.insert_alert(
        alert_id="api-alert-ml-ack",
        device_id=DEVICE,
        alert_type="fall_detected",
        source="ml",
    )
    body = client.post("/api/alerts/api-alert-ml-ack/ack").json()
    assert body["status"] == "acknowledged"
    assert body["ack_sent_to_device"] is False


def test_acknowledging_unknown_alert_is_404():
    assert client.post("/api/alerts/nope/ack").status_code == 404


def test_command_whitelist_rejects_anything_else():
    response = client.post(f"/api/devices/{DEVICE}/command", json={"cmd": "reboot"})
    assert response.status_code == 400
    assert "cmd must be one of" in response.json()["detail"]
