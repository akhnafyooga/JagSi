"""Azure IoT Hub transport (issue #8): Event Grid parsing, SAS tokens, direct
methods, and the webhook end to end against the real Bridge and Store.

No Azure account is needed: Event Grid deliveries are built from the documented
event schema, and the HTTPS client for direct methods is a fake.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import urllib.parse

import pytest
from fastapi.testclient import TestClient

from app import azure_iot
from app.azure_iot import (
    DirectMethodSender,
    EventGridError,
    generate_sas_token,
    parse_eventgrid,
)
from app.config import settings
from app.main import app, bridge, store

DEVICE = "jagsi-watch-01"
HUB = "jagsi-hub.azure-devices.net"
KEY = base64.b64encode(b"0123456789abcdef0123456789abcdef").decode()


def telemetry_event(body, kind="telemetry", device=DEVICE, encode=False):
    if encode:
        body = base64.b64encode(json.dumps(body).encode()).decode()
    return {
        "id": "e1",
        "eventType": "Microsoft.Devices.DeviceTelemetry",
        "subject": f"devices/{device}",
        "data": {
            "body": body,
            "properties": {"type": kind},
            "systemProperties": {
                "iothub-content-type": "application/json",
                "iothub-content-encoding": "utf-8",
                "iothub-connection-device-id": device,
            },
        },
    }


# -- SAS token ---------------------------------------------------------------
def test_sas_token_signature_verifies():
    token = generate_sas_token(HUB, KEY, "service", ttl_seconds=60, now=1_700_000_000)
    assert token.startswith("SharedAccessSignature ")
    fields = dict(p.split("=", 1) for p in token.split(" ", 1)[1].split("&"))
    assert fields["sr"] == HUB
    assert fields["se"] == "1700000060"
    assert fields["skn"] == "service"
    expected = base64.b64encode(
        hmac.new(base64.b64decode(KEY), f"{HUB}\n1700000060".encode(), hashlib.sha256).digest()
    ).decode()
    assert urllib.parse.unquote(fields["sig"]) == expected


# -- Event Grid parsing ------------------------------------------------------
def test_validation_handshake_returns_code():
    out = parse_eventgrid(
        [{"eventType": "Microsoft.EventGrid.SubscriptionValidationEvent", "data": {"validationCode": "abc"}}]
    )
    assert out.validation_code == "abc"
    assert out.messages == []


def test_json_body_becomes_bridge_message():
    out = parse_eventgrid([telemetry_event({"device_id": DEVICE, "heart_rate": 70})])
    assert out.messages == [("telemetry", {"device_id": DEVICE, "heart_rate": 70})]


def test_base64_body_is_decoded():
    """Without content type and encoding, IoT Hub base64-encodes the body."""
    out = parse_eventgrid([telemetry_event({"device_id": DEVICE, "seq": 3}, encode=True)])
    assert out.messages[0][1]["seq"] == 3


def test_device_id_comes_from_iot_hub_when_payload_omits_it():
    out = parse_eventgrid([telemetry_event({"heart_rate": 70})])
    assert out.messages[0][1]["device_id"] == DEVICE


def test_spoofed_device_id_is_refused():
    """A watch must not be able to report telemetry, or a fall, for another elder."""
    with pytest.raises(EventGridError):
        parse_eventgrid([telemetry_event({"device_id": "jagsi-watch-02"}, device=DEVICE)])


def test_unknown_message_type_is_skipped():
    out = parse_eventgrid([telemetry_event({"device_id": DEVICE}, kind="cmd")])
    assert out.messages == [] and out.skipped == 1


def test_connection_events_become_status():
    events = [
        {"eventType": "Microsoft.Devices.DeviceConnected", "data": {"deviceId": DEVICE}},
        {"eventType": "Microsoft.Devices.DeviceDisconnected", "data": {"deviceId": DEVICE}},
    ]
    out = parse_eventgrid(events)
    assert out.messages == [
        ("status", {"device_id": DEVICE, "state": "online"}),
        ("status", {"device_id": DEVICE, "state": "offline"}),
    ]


def test_cloudevents_type_field_is_accepted():
    event = telemetry_event({"device_id": DEVICE})
    event["type"] = event.pop("eventType")
    assert len(parse_eventgrid([event]).messages) == 1


def test_non_list_delivery_is_refused():
    with pytest.raises(EventGridError):
        parse_eventgrid({"eventType": "x"})


# -- direct methods ----------------------------------------------------------
class FakeResponse:
    def __init__(self, status_code=200, body=None):
        self.status_code = status_code
        self._body = body if body is not None else {"status": 200, "payload": {}}
        self.text = json.dumps(self._body)

    def json(self):
        return self._body


class FakeHttp:
    def __init__(self, response=None):
        self.response = response or FakeResponse()
        self.calls = []

    def post(self, url, json=None, headers=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        return self.response

    def close(self):
        pass


def test_direct_method_request_shape():
    http = FakeHttp()
    sender = DirectMethodSender(HUB, "service", KEY, client=http)
    assert sender.invoke(DEVICE, {"cmd": "ack_alert", "event_id": "ev-1"}) is True
    call = http.calls[0]
    assert call["url"] == f"https://{HUB}/twins/{DEVICE}/methods?api-version=2021-04-12"
    assert call["json"]["methodName"] == "ack_alert"
    assert call["json"]["payload"] == {"event_id": "ev-1"}
    assert call["headers"]["Authorization"].startswith("SharedAccessSignature sr=")
    sender.close()


def test_offline_device_reports_failure():
    sender = DirectMethodSender(HUB, "service", KEY, client=FakeHttp(FakeResponse(404, {"Message": "offline"})))
    assert sender.invoke(DEVICE, {"cmd": "ping"}) is False


def test_device_error_status_reports_failure():
    sender = DirectMethodSender(HUB, "service", KEY, client=FakeHttp(FakeResponse(200, {"status": 400})))
    assert sender.invoke(DEVICE, {"cmd": "set_interval", "ms": 5}) is False


# -- webhook end to end ------------------------------------------------------
class RecordingSender:
    def __init__(self):
        self.sent = []

    def invoke(self, device_id, command):
        self.sent.append((device_id, command, "wait"))
        return True

    def invoke_background(self, device_id, command):
        self.sent.append((device_id, command, "background"))
        return True

    def close(self):
        pass


@pytest.fixture
def azure_mode(monkeypatch):
    monkeypatch.setattr(settings, "ingest_mode", "azure")
    monkeypatch.setattr(settings, "eventgrid_key", "s3cret")
    sender = RecordingSender()
    monkeypatch.setattr(bridge, "command_sender", sender)
    return sender


client = TestClient(app)


def test_webhook_is_off_in_mqtt_mode():
    assert client.post("/api/ingest/eventgrid?key=x", json=[]).status_code == 404


def test_webhook_rejects_wrong_key(azure_mode):
    assert client.post("/api/ingest/eventgrid?key=nope", json=[]).status_code == 401


def test_webhook_answers_validation(azure_mode):
    body = [{"eventType": "Microsoft.EventGrid.SubscriptionValidationEvent", "data": {"validationCode": "v-42"}}]
    resp = client.post("/api/ingest/eventgrid?key=s3cret", json=body)
    assert resp.status_code == 200
    assert resp.json() == {"validationResponse": "v-42"}


def test_webhook_stores_telemetry(azure_mode):
    msg = {
        "device_id": "jagsi-watch-az",
        "seq": 41,
        "ts": "2026-11-09T07:00:00Z",
        "heart_rate": 81,
        "spo2": 97.5,
        "body_temperature": 36.7,
        "accel": {"x": 0, "y": 0, "z": 1},
        "accel_peak_g": 1.0,
        "battery_level": 90,
        "sim": True,
    }
    resp = client.post("/api/ingest/eventgrid?key=s3cret", json=[telemetry_event(msg, device="jagsi-watch-az")])
    assert resp.json() == {"accepted": 1, "skipped": 0}
    latest = store.latest_telemetry("jagsi-watch-az")
    assert latest["seq"] == 41 and latest["heart_rate"] == 81


def test_webhook_event_creates_alert_and_acks_in_background(azure_mode):
    event = {
        "device_id": "jagsi-watch-az",
        "event_id": "jagsi-watch-az-boot1-1",
        "ts": "2026-11-09T07:00:05Z",
        "alert_type": "manual_sos",
        "status": "unresolved",
        "attempt": 1,
    }
    resp = client.post(
        "/api/ingest/eventgrid?key=s3cret",
        json=[telemetry_event(event, kind="event", device="jagsi-watch-az")],
    )
    assert resp.json()["accepted"] == 1
    ids = [a["alert_id"] for a in store.recent_alerts(device_id="jagsi-watch-az")]
    assert "jagsi-watch-az-boot1-1" in ids
    assert ("jagsi-watch-az", {"cmd": "ack_alert", "event_id": "jagsi-watch-az-boot1-1"}, "background") in azure_mode.sent


def test_webhook_disconnect_marks_device_offline(azure_mode):
    store.upsert_device({"device_id": "jagsi-watch-az", "state": "online", "fw": "0.2.0"})
    client.post(
        "/api/ingest/eventgrid?key=s3cret",
        json=[{"eventType": "Microsoft.Devices.DeviceDisconnected", "data": {"deviceId": "jagsi-watch-az"}}],
    )
    device = store.device("jagsi-watch-az")
    assert device["state"] == "offline"
    assert device["fw"] == "0.2.0"     # a status without fw must not wipe it


def test_webhook_refuses_spoofed_batch(azure_mode):
    resp = client.post(
        "/api/ingest/eventgrid?key=s3cret",
        json=[telemetry_event({"device_id": "someone-else"}, device="jagsi-watch-az")],
    )
    assert resp.status_code == 400


def test_command_endpoint_uses_direct_method(azure_mode):
    resp = client.post(f"/api/devices/{DEVICE}/command", json={"cmd": "ping"})
    assert resp.status_code == 200
    assert (DEVICE, {"cmd": "ping"}, "wait") in azure_mode.sent


def test_azure_mode_requires_secrets(monkeypatch):
    from app import main

    monkeypatch.setattr(settings, "ingest_mode", "azure")
    monkeypatch.setattr(settings, "azure_iothub_hostname", HUB)
    monkeypatch.setattr(settings, "azure_service_key", KEY)
    monkeypatch.setattr(settings, "eventgrid_key", "")
    with pytest.raises(RuntimeError):
        main._command_sender()


def test_module_has_no_hardcoded_secrets():
    source = open(azure_iot.__file__, encoding="utf-8").read()
    assert "SharedAccessKey=" not in source
