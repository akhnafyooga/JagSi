"""Persistence behaviour the pipeline depends on."""

from __future__ import annotations

import pytest

from app.store import Store


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path / "t.db")


def telemetry(**over):
    msg = {
        "device_id": "jagsi-watch-01",
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
    msg.update(over)
    return msg


def test_telemetry_round_trip(store):
    store.insert_telemetry(telemetry())
    row = store.latest_telemetry("jagsi-watch-01")
    assert row["heart_rate"] == 78
    assert row["body_temperature"] == 36.6
    assert row["accel_z"] == 1.0
    assert row["simulated"] == 1
    assert row["ts_source"] == "device"


def test_unsynced_clock_falls_back_to_server_time(store):
    """The device sends ts: null until NTP resolves. The row must still be usable
    and must say the timestamp was substituted."""
    store.insert_telemetry(telemetry(ts=None))
    row = store.latest_telemetry("jagsi-watch-01")
    assert row["ts_source"] == "server"
    assert row["timestamp"] == row["received_at"]


def test_history_is_oldest_first_and_capped(store):
    for i in range(10):
        store.insert_telemetry(telemetry(seq=i, heart_rate=60 + i))
    points = store.telemetry_history("jagsi-watch-01", limit=5)
    assert len(points) == 5
    assert [p["heart_rate"] for p in points] == [65, 66, 67, 68, 69]


def test_latest_telemetry_is_none_for_unknown_device(store):
    assert store.latest_telemetry("nope") is None


def test_duplicate_alert_is_counted_not_reinserted(store):
    """The firmware re-sends an unacknowledged event up to five times with the
    same event_id. The caregiver must see one alert, not five."""
    args = dict(
        alert_id="jagsi-watch-01-abc-1",
        device_id="jagsi-watch-01",
        alert_type="fall_detected",
        source="device_rule",
    )
    assert store.insert_alert(**args) is True
    for _ in range(4):
        assert store.insert_alert(**args) is False

    alerts = store.recent_alerts()
    assert len(alerts) == 1
    assert alerts[0]["attempts"] == 5


def test_acknowledge_alert(store):
    store.insert_alert(
        alert_id="a1", device_id="d1", alert_type="manual_sos", source="device_rule"
    )
    assert store.acknowledge_alert("a1") is True
    assert store.recent_alerts()[0]["status"] == "acknowledged"
    assert store.acknowledge_alert("missing") is False


def test_last_device_alert_at_ignores_ml_alerts(store):
    """Duplicate suppression only looks at device-rule alerts; otherwise an ML
    alert would suppress the next ML alert through the wrong code path."""
    store.insert_alert(
        alert_id="ml-1", device_id="d1", alert_type="fall_detected", source="ml"
    )
    assert store.last_device_alert_at("d1", "fall_detected") is None

    store.insert_alert(
        alert_id="dev-1", device_id="d1", alert_type="fall_detected", source="device_rule"
    )
    assert store.last_device_alert_at("d1", "fall_detected") is not None


def test_device_upsert_keeps_known_fields_on_a_bare_lwt(store):
    """The Last Will payload is only {device_id, state}. Applying it must not wipe
    the firmware version and battery level learned from the full status message."""
    store.upsert_device(
        {
            "device_id": "d1",
            "state": "online",
            "fw": "0.1.0",
            "battery_level": 87,
            "ip": "10.10.0.2",
            "interval_ms": 2000,
            "motion_enabled": True,
        }
    )
    store.upsert_device({"device_id": "d1", "state": "offline"})

    device = store.device("d1")
    assert device["state"] == "offline"
    assert device["fw"] == "0.1.0"
    assert device["battery_level"] == 87
    assert device["motion_enabled"] == 1
