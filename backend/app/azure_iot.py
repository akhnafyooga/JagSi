"""Azure IoT Hub transport: Event Grid in, direct methods out (issue #8).

Until Week 6 the device and the backend met on the public HiveMQ broker, which has
no password, so anyone could read or inject telemetry. With ``JAGSI_INGEST=azure``
the device talks only to Azure IoT Hub (TLS, X.509 device certificate) and the
backend never holds an MQTT connection at all:

    ESP32 --MQTT/TLS--> IoT Hub --Event Grid--> POST /api/ingest/eventgrid
    backend --HTTPS direct method--> IoT Hub --MQTT--> ESP32

Inbound: IoT Hub publishes every device-to-cloud message to Event Grid as a
``Microsoft.Devices.DeviceTelemetry`` event, and connection changes as
``DeviceConnected`` / ``DeviceDisconnected``. ``parse_eventgrid`` turns those into
the same ``(kind, payload)`` pairs the MQTT bridge already handles, so every rule
from Week 6 (window validation, duplicate suppression, alert acks) applies
unchanged.

Outbound: commands (ack_alert, ping, set_interval, set_motion) become IoT Hub
direct methods, invoked over the REST API with a service SAS token. A direct method
reports back whether the device received it, which the public broker never could.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

log = logging.getLogger("jagsi.azure")

# The four message kinds the firmware sends. Anything else is dropped, so a
# device cannot reach a handler the backend does not expect.
DEVICE_KINDS = {"telemetry", "motion", "event", "status"}

EVENT_VALIDATION = "Microsoft.EventGrid.SubscriptionValidationEvent"
EVENT_TELEMETRY = "Microsoft.Devices.DeviceTelemetry"
EVENT_CONNECTED = "Microsoft.Devices.DeviceConnected"
EVENT_DISCONNECTED = "Microsoft.Devices.DeviceDisconnected"

DIRECT_METHOD_API_VERSION = "2021-04-12"


# ---------------------------------------------------------------------------
# SAS tokens
# ---------------------------------------------------------------------------
def generate_sas_token(
    resource_uri: str,
    key_b64: str,
    policy_name: Optional[str] = None,
    ttl_seconds: int = 3600,
    now: Optional[float] = None,
) -> str:
    """Builds an IoT Hub shared access signature.

    ``resource_uri`` is the hub host name for service calls (for example
    ``jagsi-hub.azure-devices.net``). The key is the base64 primary key of a
    shared access policy that has the ``ServiceConnect`` permission. Using the
    ``service`` policy rather than ``iothubowner`` keeps the backend unable to
    create or delete devices, which it never needs to do.
    """
    expiry = int((now if now is not None else time.time()) + ttl_seconds)
    encoded_uri = urllib.parse.quote(resource_uri, safe="").lower()
    to_sign = f"{encoded_uri}\n{expiry}".encode("utf-8")
    digest = hmac.new(base64.b64decode(key_b64), to_sign, hashlib.sha256).digest()
    signature = urllib.parse.quote(base64.b64encode(digest), safe="")
    token = f"SharedAccessSignature sr={encoded_uri}&sig={signature}&se={expiry}"
    if policy_name:
        token += f"&skn={policy_name}"
    return token


# ---------------------------------------------------------------------------
# Event Grid -> bridge
# ---------------------------------------------------------------------------
class EventGridError(ValueError):
    """An Event Grid delivery the backend refuses to process."""


@dataclass
class ParsedDelivery:
    """What one Event Grid POST contained."""

    validation_code: Optional[str] = None
    messages: List[Tuple[str, Dict[str, Any]]] = None  # (kind, payload)
    skipped: int = 0

    def __post_init__(self) -> None:
        if self.messages is None:
            self.messages = []


def _decode_body(body: Any) -> Any:
    """Returns the device JSON from a DeviceTelemetry event.

    When the device sets content type application/json and encoding utf-8, Event
    Grid hands the body over as a JSON object. If either is missing, IoT Hub
    base64-encodes it, so that case is decoded too rather than silently dropped.
    """
    if isinstance(body, dict):
        return body
    if isinstance(body, str):
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            pass
        try:
            return json.loads(base64.b64decode(body, validate=True).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise EventGridError("telemetry body is neither JSON nor base64 JSON") from exc
    raise EventGridError(f"telemetry body has unexpected type {type(body).__name__}")


def _device_from_event(event: Dict[str, Any]) -> Optional[str]:
    data = event.get("data") or {}
    system = data.get("systemProperties") or {}
    device = system.get("iothub-connection-device-id") or data.get("deviceId")
    if device:
        return device
    subject = event.get("subject") or ""          # "devices/<id>"
    if subject.startswith("devices/"):
        return subject.split("/", 2)[1]
    return None


def parse_eventgrid(events: Iterable[Dict[str, Any]]) -> ParsedDelivery:
    """Converts an Event Grid batch into bridge messages.

    The device id comes from IoT Hub's ``iothub-connection-device-id``, which IoT
    Hub sets from the authenticated connection. A payload whose own ``device_id``
    differs is refused: otherwise one compromised watch could publish telemetry
    or a fake fall alert in another elder's name.
    """
    out = ParsedDelivery()
    if not isinstance(events, list):
        raise EventGridError("Event Grid must POST a JSON array of events")

    for event in events:
        if not isinstance(event, dict):
            out.skipped += 1
            continue
        etype = event.get("eventType") or event.get("type")

        if etype == EVENT_VALIDATION:
            out.validation_code = (event.get("data") or {}).get("validationCode")
            continue

        device_id = _device_from_event(event)
        if not device_id:
            out.skipped += 1
            log.warning("event %s without a device id, skipped", event.get("id"))
            continue

        if etype in (EVENT_CONNECTED, EVENT_DISCONNECTED):
            state = "online" if etype == EVENT_CONNECTED else "offline"
            out.messages.append(("status", {"device_id": device_id, "state": state}))
            continue

        if etype != EVENT_TELEMETRY:
            out.skipped += 1
            continue

        data = event.get("data") or {}
        kind = (data.get("properties") or {}).get("type")
        if kind not in DEVICE_KINDS:
            out.skipped += 1
            log.warning("telemetry from %s with type %r, skipped", device_id, kind)
            continue

        payload = _decode_body(data.get("body"))
        if not isinstance(payload, dict):
            out.skipped += 1
            continue
        claimed = payload.get("device_id")
        if claimed is not None and claimed != device_id:
            raise EventGridError(
                f"payload claims device_id {claimed!r} but IoT Hub authenticated {device_id!r}"
            )
        payload["device_id"] = device_id
        out.messages.append((kind, payload))
    return out


# ---------------------------------------------------------------------------
# bridge -> device (direct methods)
# ---------------------------------------------------------------------------
class DirectMethodSender:
    """Sends commands to a device as IoT Hub direct methods over HTTPS.

    The method name is the command (``ack_alert``), and the payload is the rest
    of the command object (``{"event_id": ...}``). The firmware rebuilds the same
    JSON it used to get on the ``cmd`` topic, so one command handler serves both
    transports.
    """

    def __init__(
        self,
        hostname: str,
        policy_name: str,
        policy_key: str,
        response_timeout_s: int = 5,
        client: Any = None,
    ) -> None:
        if not hostname or not policy_key:
            raise ValueError("IoT Hub host name and service policy key are required")
        self.hostname = hostname
        self.policy_name = policy_name
        self.policy_key = policy_key
        self.response_timeout_s = response_timeout_s
        self._client = client
        self._token: Optional[str] = None
        self._token_expiry = 0.0
        self._pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="jagsi-dm")

    def _http(self):
        if self._client is None:
            import httpx  # imported here so MQTT-only installs do not need it

            self._client = httpx.Client(timeout=self.response_timeout_s + 10)
        return self._client

    def _auth(self) -> str:
        now = time.time()
        if self._token is None or now > self._token_expiry - 300:
            self._token = generate_sas_token(self.hostname, self.policy_key, self.policy_name, 3600, now)
            self._token_expiry = now + 3600
        return self._token

    def invoke(self, device_id: str, command: Dict[str, Any]) -> bool:
        """Calls the direct method and waits for the device's answer.

        Returns False when the device is offline (IoT Hub answers 404) or does
        not answer in time (504), so the API can tell the caregiver the command
        did not arrive instead of pretending it did.
        """
        method = command.get("cmd")
        if not method:
            raise ValueError("command needs a 'cmd' field")
        payload = {k: v for k, v in command.items() if k != "cmd"}
        url = (
            f"https://{self.hostname}/twins/{urllib.parse.quote(device_id, safe='')}"
            f"/methods?api-version={DIRECT_METHOD_API_VERSION}"
        )
        body = {
            "methodName": method,
            "responseTimeoutInSeconds": self.response_timeout_s,
            "connectTimeoutInSeconds": 0,
            "payload": payload,
        }
        try:
            resp = self._http().post(
                url,
                json=body,
                headers={"Authorization": self._auth(), "Content-Type": "application/json"},
            )
        except Exception as exc:  # network error, DNS, TLS
            log.warning("direct method %s to %s failed: %s", method, device_id, exc)
            return False
        if resp.status_code != 200:
            log.warning(
                "direct method %s to %s returned HTTP %s: %s",
                method, device_id, resp.status_code, resp.text[:200],
            )
            return False
        try:
            status = resp.json().get("status")
        except ValueError:
            status = None
        ok = status is None or 200 <= int(status) < 300
        if not ok:
            log.warning("device answered %s to %s with status %s", device_id, method, status)
        return ok

    def invoke_background(self, device_id: str, command: Dict[str, Any]) -> bool:
        """Fire and forget, for acks sent while handling an Event Grid request.

        Event Grid retries a delivery that takes too long, so the webhook must
        not wait up to five seconds for the watch to answer.
        """
        self._pool.submit(self.invoke, device_id, command)
        return True

    def close(self) -> None:
        self._pool.shutdown(wait=False)
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
