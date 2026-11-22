"""The firmware-to-model contract.

This is the test that should have existed before issue #9 was reported as working.
The model's accuracy figures were measured on windows built inside Python. Nothing
checked that the window the *device* publishes has the shape the model expects, and
it did not: the firmware was sending one sample per message plus a peak value.

Each test here states one rule from docs/mqtt-contract.md section 3.5.
"""

from __future__ import annotations

import json
import math

import pytest

from app.bridge import WindowRejected, parse_window
from ml.schema import SAMPLE_RATE_HZ, WINDOW_SIZE


def make_payload(rows=None, **overrides):
    """A valid motion payload, exactly as sketch.ino serializes it."""
    if rows is None:
        rows = [[0.01, -0.02, 1.00, 0.5, -0.3, 0.1] for _ in range(WINDOW_SIZE)]
    payload = {
        "device_id": "jagsi-watch-01",
        "seq": 12,
        "ts": "2026-11-04T12:00:03Z",
        "t0_ms": 84000,
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "window_size": WINDOW_SIZE,
        "dropped": 0,
        "sim": True,
        "s": rows,
    }
    payload.update(overrides)
    return payload


# -- the contract holds --------------------------------------------------------
def test_valid_window_parses_to_thirty_samples():
    samples = parse_window(make_payload())
    assert len(samples) == WINDOW_SIZE == 30


def test_field_order_maps_to_accelsample():
    """s[i] is positional: [ax, ay, az, gx, gy, gz]."""
    rows = [[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]] + [
        [0.0, 0.0, 1.0, 0.0, 0.0, 0.0] for _ in range(WINDOW_SIZE - 1)
    ]
    first = parse_window(make_payload(rows))[0]
    assert (first.ax, first.ay, first.az) == (1.0, 2.0, 3.0)
    assert (first.gx, first.gy, first.gz) == (4.0, 5.0, 6.0)


def test_chronological_order_is_preserved():
    rows = [[float(i), 0.0, 1.0, 0.0, 0.0, 0.0] for i in range(WINDOW_SIZE)]
    samples = parse_window(make_payload(rows))
    assert [s.ax for s in samples] == [float(i) for i in range(WINDOW_SIZE)]


def test_payload_fits_the_firmware_mqtt_buffer():
    """sketch.ino sets mqtt.setBufferSize(2048) and a 1600 byte serialize buffer."""
    encoded = json.dumps(make_payload(), separators=(",", ":"))
    assert len(encoded) < 1600, f"payload is {len(encoded)} bytes, serialize buffer is 1600"


# -- the contract is violated --------------------------------------------------
def test_rejects_wrong_sample_rate():
    with pytest.raises(WindowRejected, match="sample_rate_hz"):
        parse_window(make_payload(sample_rate_hz=20))


def test_rejects_wrong_window_size_field():
    with pytest.raises(WindowRejected, match="window_size"):
        parse_window(make_payload(window_size=25))


def test_rejects_short_window():
    rows = [[0.0, 0.0, 1.0, 0.0, 0.0, 0.0] for _ in range(WINDOW_SIZE - 1)]
    with pytest.raises(WindowRejected, match="rows"):
        parse_window(make_payload(rows, window_size=WINDOW_SIZE))


def test_rejects_window_with_dropped_samples():
    """Broken 10 Hz spacing makes every timing feature wrong, so do not score it."""
    with pytest.raises(WindowRejected, match="dropped"):
        parse_window(make_payload(dropped=3))


def test_rejects_row_with_missing_axis():
    rows = [[0.0, 0.0, 1.0, 0.0, 0.0, 0.0] for _ in range(WINDOW_SIZE)]
    rows[5] = [0.0, 0.0, 1.0]
    with pytest.raises(WindowRejected, match="row 5"):
        parse_window(make_payload(rows))


def test_rejects_non_numeric_value():
    rows = [[0.0, 0.0, 1.0, 0.0, 0.0, 0.0] for _ in range(WINDOW_SIZE)]
    rows[9] = [0.0, "nan-ish", 1.0, 0.0, 0.0, 0.0]
    with pytest.raises(WindowRejected, match="row 9"):
        parse_window(make_payload(rows))


def test_telemetry_message_is_not_a_window():
    """The old pipeline fed this to the model. It must be refused outright."""
    telemetry = {
        "device_id": "jagsi-watch-01",
        "seq": 42,
        "heart_rate": 78,
        "accel": {"x": 0.0, "y": 0.0, "z": 1.0},
        "accel_peak_g": 1.0,
    }
    with pytest.raises(WindowRejected):
        parse_window(telemetry)


# -- the model actually scores what the device sends ---------------------------
def _fall_like_window():
    """A window shaped like the synthetic falls the model was trained on:
    upright, then free fall, then an impact spike, then lying still."""
    rows = []
    for _ in range(8):                        # upright and walking
        rows.append([0.05, 0.05, 1.0, 2.0, 1.0, 0.5])
    for _ in range(4):                        # free fall, SMV well under 0.5 g
        rows.append([0.05, 0.05, 0.15, 30.0, 20.0, 10.0])
    rows.append([1.2, 1.5, 2.6, 250.0, 180.0, 120.0])   # impact, SMV over 2 g
    rows.append([0.6, 0.7, 1.4, 90.0, 60.0, 40.0])      # ring-down
    while len(rows) < 30:                     # lying still, tilted
        rows.append([0.95, 0.1, 0.08, 0.5, 0.3, 0.2])
    return rows[:30]


def _still_window():
    return [[0.01, 0.01, 1.0, 0.2, 0.1, 0.05] for _ in range(30)]


@pytest.fixture(scope="module")
def classifier():
    joblib = pytest.importorskip("joblib")
    from app.config import settings
    from ml.inference import FallClassifier

    try:
        return FallClassifier.load(settings.model_path)
    except FileNotFoundError:
        pytest.skip("trained artifact not present")


def test_classifier_accepts_a_device_shaped_window(classifier):
    """End to end: raw MQTT payload -> parse_window -> predict_window."""
    samples = parse_window(make_payload(_still_window()))
    result = classifier.predict_window(samples)
    assert isinstance(result.is_fall, bool)
    assert 0.0 <= result.confidence <= 1.0
    assert result.label in {"fall", "non_fall"}


def test_all_eighteen_features_are_finite_on_a_device_window(classifier):
    """A short window or a NaN silently poisons the feature vector."""
    samples = parse_window(make_payload(_fall_like_window()))
    features, _ = classifier.predict_proba(samples)
    assert len(features) == 18
    for name, value in features.items():
        assert math.isfinite(value), f"feature {name} is {value}"


def test_still_window_is_not_a_fall(classifier):
    samples = parse_window(make_payload(_still_window()))
    assert classifier.predict_window(samples).is_fall is False


def test_fall_shaped_window_is_flagged(classifier):
    samples = parse_window(make_payload(_fall_like_window()))
    result = classifier.predict_window(samples)
    assert result.is_fall is True, f"confidence was {result.confidence:.3f}"
