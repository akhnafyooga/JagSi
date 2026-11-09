"""Labelled motion recording for re-tuning the fall threshold (issue #9)."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.main import app, bridge, recorder
from app.recorder import MotionRecorder, RecordingError, is_fall_label

client = TestClient(app)


def window(device="jagsi-watch-01", seq=1):
    return {
        "device_id": device,
        "seq": seq,
        "sample_rate_hz": 10,
        "window_size": 30,
        "dropped": 0,
        "s": [[0.0, 0.0, 1.0, 0.0, 0.0, 0.0]] * 30,
    }


def test_session_writes_jsonl(tmp_path):
    rec = MotionRecorder(tmp_path)
    info = rec.start("walking", "s01")
    assert rec.record(window(seq=1)) and rec.record(window(seq=2))
    done = rec.stop()
    assert done["windows"] == 2
    lines = [json.loads(l) for l in open(info["path"], encoding="utf-8")]
    assert [l["window"]["seq"] for l in lines] == [1, 2]
    assert lines[0]["label"] == "walking" and lines[0]["is_fall"] is False
    assert lines[0]["subject"] == "s01"


def test_fall_labels():
    assert is_fall_label("fall_side") and is_fall_label("fall_forward")
    assert not is_fall_label("sit_down_hard")


def test_device_filter(tmp_path):
    rec = MotionRecorder(tmp_path)
    rec.start("still", "s01", device_id="jagsi-watch-01")
    assert rec.record(window("jagsi-watch-02")) is False
    assert rec.record(window("jagsi-watch-01")) is True


@pytest.mark.parametrize("label,subject", [("Walking!", "s01"), ("walking", ""), ("../x", "s01")])
def test_unsafe_names_are_refused(tmp_path, label, subject):
    with pytest.raises(RecordingError):
        MotionRecorder(tmp_path).start(label, subject)


def test_sessions_in_the_same_second_get_their_own_file(tmp_path):
    rec = MotionRecorder(tmp_path)
    names = []
    for _ in range(3):
        names.append(rec.start("fall_side", "s01")["session"])
        rec.stop()
    assert len(set(names)) == 3
    assert len(list(tmp_path.glob("*.jsonl"))) == 3


def test_one_session_at_a_time(tmp_path):
    rec = MotionRecorder(tmp_path)
    rec.start("still", "s01")
    with pytest.raises(RecordingError):
        rec.start("walking", "s01")
    rec.stop()
    with pytest.raises(RecordingError):
        rec.stop()


def test_bridge_records_even_without_classifier(tmp_path, monkeypatch):
    rec = MotionRecorder(tmp_path)
    monkeypatch.setattr(bridge, "recorder", rec)
    monkeypatch.setattr(bridge, "_classifier", None)
    rec.start("stairs", "s02")
    bridge.dispatch("motion", window(seq=9))
    assert rec.stop()["windows"] == 1


def test_recording_endpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(recorder, "directory", tmp_path)
    assert client.get("/api/recording").json()["active"] is False
    started = client.post("/api/recording/start", json={"label": "lie_down", "subject": "s03"}).json()
    assert started["label"] == "lie_down"
    assert client.post("/api/recording/start", json={"label": "still", "subject": "s03"}).status_code == 400
    stopped = client.post("/api/recording/stop").json()
    assert stopped["session"] == started["session"]
    assert client.post("/api/recording/stop").status_code == 400
