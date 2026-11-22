"""Input checks added for the public-broker demo (issue #21, section 7).

The public MQTT broker cannot authenticate publishers, so the bridge checks every
message against the topic it arrived on, and never scores a window holding NaN,
Infinity or booleans: json.loads accepts all three and float() converts them.
"""

from __future__ import annotations

import dataclasses
import json
import math

import pytest

from app.bridge import Bridge, WindowRejected, parse_window
from app.config import settings
from app.store import Store

from ml.schema import WINDOW_SIZE

from .test_window_contract import make_payload


def still_rows():
    return [[0.01, -0.02, 1.00, 0.5, -0.3, 0.1] for _ in range(WINDOW_SIZE)]


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_non_finite_samples_are_rejected(bad):
    rows = still_rows()
    rows[7][2] = bad
    with pytest.raises(WindowRejected, match="NaN or Infinity"):
        parse_window(make_payload(rows))


def test_nan_from_json_text_is_rejected():
    rows = still_rows()
    text = json.dumps(make_payload(rows)).replace("1.0", "NaN", 1)
    with pytest.raises(WindowRejected):
        parse_window(json.loads(text))


def test_boolean_sample_is_rejected():
    rows = still_rows()
    rows[0][0] = True
    with pytest.raises(WindowRejected, match="boolean"):
        parse_window(make_payload(rows))


class Message:
    def __init__(self, topic: str, payload: dict | bytes) -> None:
        self.topic = topic
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()


@pytest.fixture
def make_bridge(tmp_path):
    def build(**overrides):
        cfg = dataclasses.replace(settings, **overrides)
        bridge = Bridge(cfg, Store(tmp_path / "bridge.db"))
        handled = []
        bridge.dispatch = lambda kind, payload: handled.append((kind, payload["device_id"]))
        return bridge, handled

    return build


def telemetry_topic(device: str) -> str:
    return settings.topic("telemetry", device)


def test_device_id_must_match_topic(make_bridge):
    bridge, handled = make_bridge()
    bridge._on_message(None, None, Message(telemetry_topic("jagsi-watch-01"),
                                           {"device_id": "intruder"}))
    assert handled == []
    assert bridge.stats["messages_rejected"] == 1
    assert "does not match topic" in bridge.stats["last_message_reject_reason"]


def test_matching_device_is_dispatched(make_bridge):
    bridge, handled = make_bridge()
    bridge._on_message(None, None, Message(telemetry_topic("jagsi-watch-01"),
                                           {"device_id": "jagsi-watch-01"}))
    assert handled == [("telemetry", "jagsi-watch-01")]


def test_restricted_bridge_drops_other_devices(make_bridge):
    bridge, handled = make_bridge(restrict_device=True, device_id="jagsi-watch-01")
    bridge._on_message(None, None, Message(telemetry_topic("other-watch"),
                                           {"device_id": "other-watch"}))
    assert handled == []
    assert "unexpected device" in bridge.stats["last_message_reject_reason"]


def test_oversized_payload_is_dropped_before_parsing(make_bridge):
    bridge, handled = make_bridge(max_payload_bytes=100)
    bridge._on_message(None, None, Message(telemetry_topic("jagsi-watch-01"),
                                           b"{" + b" " * 200 + b"}"))
    assert handled == []
    assert "limit 100" in bridge.stats["last_message_reject_reason"]


def test_refused_connection_is_visible(make_bridge):
    bridge, _ = make_bridge()
    bridge._on_connect(None, None, None, "Not authorized")
    assert bridge.stats["connected"] is False
    assert bridge.stats["last_connect_error"] == "Not authorized"
