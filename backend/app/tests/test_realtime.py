"""Real-time emergency notifications (issue #13).

Covers the thread-safe hub behind /api/stream and /ws/alerts, and the WebSocket
protocol the dashboard's emergency screen relies on.
"""

from __future__ import annotations

import asyncio
import threading
import time

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import main
from app.main import app, store
from app.realtime import ALERT_EVENTS, Hub

client = TestClient(app)
DEVICE = "jagsi-watch-01"


def _alert(alert_id: str, source: str = "ml", alert_type: str = "fall_detected", **kw) -> None:
    store.insert_alert(alert_id=alert_id, device_id=DEVICE, alert_type=alert_type, source=source, **kw)


def _receive_until(ws, kind: str, limit: int = 10) -> dict:
    """Reads past pings until a message of ``kind`` arrives."""
    for _ in range(limit):
        msg = ws.receive_json()
        if msg["type"] == kind:
            return msg
    raise AssertionError(f"no {kind!r} message in {limit} reads")


# -- the hub ----------------------------------------------------------------
def test_publish_from_another_thread_wakes_the_listener_immediately():
    """The Week 6 SSE code used asyncio.Queue.put_nowait from worker threads,
    which does not wake the loop by itself (a bare thread waited 15 s). The hub
    must deliver promptly no matter which thread publishes."""
    hub = Hub()

    async def scenario() -> float:
        sub = hub.subscribe()
        started = time.monotonic()
        threading.Timer(0.05, hub.publish, args=({"type": "alert", "data": {"alert_id": "x"}},)).start()
        event = await asyncio.wait_for(sub.queue.get(), timeout=2.0)
        assert event["data"]["alert_id"] == "x"
        return time.monotonic() - started

    elapsed = asyncio.run(scenario())
    assert elapsed < 0.5, f"cross-thread event took {elapsed:.2f}s to arrive"


def test_alert_listeners_do_not_receive_telemetry():
    hub = Hub()

    async def scenario():
        everything = hub.subscribe()
        alerts_only = hub.subscribe(ALERT_EVENTS)
        assert hub.publish({"type": "telemetry", "data": {}}) == 1
        assert hub.publish({"type": "alert", "data": {}}) == 2
        await asyncio.sleep(0)
        return everything.queue.qsize(), alerts_only.queue.qsize()

    assert asyncio.run(scenario()) == (2, 1)


def test_slow_listener_loses_its_oldest_event_not_the_newest():
    hub = Hub(maxsize=2)

    async def scenario():
        sub = hub.subscribe()
        for i in range(3):
            hub.publish({"type": "alert", "data": {"n": i}})
        await asyncio.sleep(0)
        return [sub.queue.get_nowait()["data"]["n"] for _ in range(2)], sub.dropped

    kept, dropped = asyncio.run(scenario())
    assert kept == [1, 2]
    assert dropped == 1


def test_unsubscribe_stops_delivery():
    hub = Hub()

    async def scenario():
        sub = hub.subscribe()
        hub.unsubscribe(sub)
        return hub.publish({"type": "alert"}), hub.count()

    assert asyncio.run(scenario()) == (0, 0)


# -- the WebSocket ------------------------------------------------------------
def test_hello_lists_only_alerts_nobody_has_handled():
    _alert("ws-open-1", vitals={"heart_rate": 120})
    _alert("ws-done-1")
    store.acknowledge_alert("ws-done-1")

    with client.websocket_connect("/ws/alerts") as ws:
        hello = ws.receive_json()

    assert hello["type"] == "hello"
    ids = [a["alert_id"] for a in hello["data"]["open_alerts"]]
    assert "ws-open-1" in ids
    assert "ws-done-1" not in ids
    opened = next(a for a in hello["data"]["open_alerts"] if a["alert_id"] == "ws-open-1")
    # Same shape as GET /api/alerts: vitals is an object, not a JSON string.
    assert opened["vitals"] == {"heart_rate": 120}
    assert "vitals_json" not in opened


def test_new_alert_is_pushed_with_vitals_as_an_object():
    with client.websocket_connect("/ws/alerts") as ws:
        ws.receive_json()  # hello
        _alert("ws-push-1", source="device_rule", alert_type="manual_sos", vitals={"spo2": 91})
        # What the bridge does after storing an alert (raw row, vitals_json string).
        main._publish({"type": "alert", "data": store.alert("ws-push-1")})
        pushed = _receive_until(ws, "alert")

    assert pushed["data"]["alert_id"] == "ws-push-1"
    assert pushed["data"]["alert_type"] == "manual_sos"
    assert pushed["data"]["vitals"] == {"spo2": 91}


def test_telemetry_is_not_sent_on_the_alert_socket():
    with client.websocket_connect("/ws/alerts") as ws:
        ws.receive_json()
        main._publish({"type": "telemetry", "data": {"heart_rate": 70}})
        main._publish({"type": "alert_ack", "data": {"alert_id": "marker"}})
        first = _receive_until(ws, "alert_ack")
    assert first["data"]["alert_id"] == "marker"


def test_ack_over_the_socket_updates_the_store_and_every_other_dashboard():
    _alert("ws-ack-1")
    with client.websocket_connect("/ws/alerts") as caregiver, client.websocket_connect("/ws/alerts") as other:
        caregiver.receive_json()
        other.receive_json()

        caregiver.send_json({"type": "ack", "alert_id": "ws-ack-1"})
        result = _receive_until(caregiver, "ack_result")
        seen_by_other = _receive_until(other, "alert_ack")

    assert result["data"]["status"] == "acknowledged"
    assert result["data"]["already_acknowledged"] is False
    assert seen_by_other["data"]["alert_id"] == "ws-ack-1"
    assert seen_by_other["data"]["via"] == "websocket"
    assert store.alert("ws-ack-1")["status"] == "acknowledged"


def test_ack_from_the_rest_api_reaches_open_sockets_quickly():
    """POST /ack runs in FastAPI's threadpool; the socket must hear about it
    right away, not at the 20 s keepalive."""
    _alert("ws-rest-ack-1")
    with client.websocket_connect("/ws/alerts") as ws:
        ws.receive_json()
        started = time.monotonic()
        assert client.post("/api/alerts/ws-rest-ack-1/ack").status_code == 200
        msg = _receive_until(ws, "alert_ack")
        elapsed = time.monotonic() - started
    assert msg["data"] == {**msg["data"], "alert_id": "ws-rest-ack-1", "via": "api"}
    assert elapsed < 2.0


def test_acking_a_device_alert_tells_the_watch(monkeypatch):
    sent = []
    monkeypatch.setattr(main.bridge, "send_command", lambda device, cmd, **kw: sent.append((device, cmd)) or True)
    _alert("ws-dev-ack-1", source="device_rule", alert_type="manual_sos")

    with client.websocket_connect("/ws/alerts") as ws:
        ws.receive_json()
        ws.send_json({"type": "ack", "alert_id": "ws-dev-ack-1"})
        result = _receive_until(ws, "ack_result")

    assert result["data"]["ack_sent_to_device"] is True
    assert sent == [(DEVICE, {"cmd": "ack_alert", "event_id": "ws-dev-ack-1"})]


def test_acking_twice_is_reported_not_rejected():
    _alert("ws-twice-1")
    with client.websocket_connect("/ws/alerts") as ws:
        ws.receive_json()
        ws.send_json({"type": "ack", "alert_id": "ws-twice-1"})
        _receive_until(ws, "ack_result")
        ws.send_json({"type": "ack", "alert_id": "ws-twice-1"})
        second = _receive_until(ws, "ack_result")
    assert second["data"]["already_acknowledged"] is True


@pytest.mark.parametrize(
    "message, expected",
    [
        ({"type": "ack", "alert_id": "does-not-exist"}, "unknown alert does-not-exist"),
        ({"type": "ack"}, "ack needs an alert_id"),
        ({"type": "ack", "alert_id": "x" * 101}, "ack needs an alert_id"),
        ({"type": "subscribe"}, "unknown message type 'subscribe'"),
        (["not", "an", "object"], "unknown message type None"),
    ],
)
def test_bad_messages_get_an_error_and_keep_the_socket_open(message, expected):
    with client.websocket_connect("/ws/alerts") as ws:
        ws.receive_json()
        ws.send_json(message)
        error = _receive_until(ws, "error")
        ws.send_json({"type": "ping"})
        pong = _receive_until(ws, "pong")
    assert error["data"]["message"] == expected
    assert pong["type"] == "pong"


def test_non_json_and_oversized_messages_are_refused():
    with client.websocket_connect("/ws/alerts") as ws:
        ws.receive_json()
        ws.send_text("not json")
        assert _receive_until(ws, "error")["data"]["message"] == "message is not JSON"
        ws.send_text("x" * 2000)
        assert _receive_until(ws, "error")["data"]["message"] == "message too large"


def test_dashboard_origin_is_allowed():
    with client.websocket_connect("/ws/alerts", headers={"origin": "http://localhost:3000"}) as ws:
        assert ws.receive_json()["type"] == "hello"


def test_other_websites_cannot_open_the_alert_socket():
    """Browsers skip CORS for WebSockets, so a random page could otherwise
    connect and acknowledge (silence) a fall alert."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws/alerts", headers={"origin": "https://evil.example"}) as ws:
            ws.receive_json()
    assert exc.value.code == 1008


def test_health_counts_alert_sockets():
    with client.websocket_connect("/ws/alerts") as ws:
        ws.receive_json()
        body = client.get("/api/health").json()
    assert body["alert_sockets"] >= 1
