import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from jagsi_schema import split_topic, topic, validate_event, validate_status, validate_telemetry  # noqa: E402

GOOD_TELEMETRY = {
    "device_id": "jagsi-watch-01", "seq": 1, "ts": "2026-09-28T12:00:00Z", "uptime_ms": 2000,
    "heart_rate": 78, "spo2": 97.0, "body_temperature": 36.6,
    "accel": {"x": 0.0, "y": 0.0, "z": 1.0}, "gyro": {"x": 0.0, "y": 0.0, "z": 0.0},
    "accel_peak_g": 1.0, "battery_level": 87, "sim": True,
}


def test_topic_roundtrip():
    t = topic("jagsi-watch-01", "telemetry")
    assert t == "jagsi/abal/v1/jagsi-watch-01/telemetry"
    assert split_topic(t) == ("jagsi-watch-01", "telemetry")
    assert split_topic("other/topic") == (None, None)


def test_good_telemetry():
    assert validate_telemetry(GOOD_TELEMETRY) == []


def test_telemetry_nulls_allowed():
    d = dict(GOOD_TELEMETRY, ts=None, body_temperature=None)
    assert validate_telemetry(d) == []


def test_bad_telemetry():
    d = dict(GOOD_TELEMETRY, spo2=120, battery_level=150)
    problems = validate_telemetry(d)
    assert any("spo2" in p for p in problems)
    assert any("battery_level" in p for p in problems)
    assert validate_telemetry({"device_id": "x"})  # missing fields


def test_event_types():
    e = {"device_id": "d", "event_id": "d-1", "ts": None, "uptime_ms": 1, "alert_type": "manual_sos",
         "status": "unresolved", "attempt": 1, "accel_peak_g": 1.0, "vitals": {}}
    assert validate_event(e) == []
    assert validate_event(dict(e, alert_type="panic"))


def test_contract_doc_examples_are_valid():
    """Every JSON example in docs/mqtt-contract.md must pass the checks."""
    doc = (ROOT / "docs" / "mqtt-contract.md").read_text(encoding="utf-8")
    blocks = [json.loads(b) for b in re.findall(r"```json\n(.*?)```", doc, re.S)]
    assert len(blocks) == 4
    telemetry, event, status, will = blocks
    assert validate_telemetry(telemetry) == []
    assert validate_event(event) == []
    assert validate_status(status) == []
    assert validate_status(will) == []
