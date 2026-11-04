"""MQTT to database bridge, with fall classification on motion windows.

This is the piece that was missing between issue #6 (the device publishes) and
issue #9 (the model classifies): something that subscribes, validates, stores,
scores, and pushes the result to the dashboard.

Flow per topic:

    telemetry -> validate -> store in telemetry_data -> broadcast to the dashboard
    motion    -> validate window shape -> FallClassifier.predict_window()
                 -> raise an ML alert if it is a fall and not a duplicate
    event     -> store alert (source=device_rule) -> broadcast -> send ack_alert
    status    -> upsert wearable_device

Threading: paho runs its network loop on its own thread, so every callback here
runs off the event loop. Database writes are synchronous and lock-guarded in
``Store``; anything that must reach the event loop goes through
``loop.call_soon_threadsafe``.
"""

from __future__ import annotations

import json
import logging
import threading
from asyncio import AbstractEventLoop
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt

from .config import Settings
from .store import Store, utcnow

log = logging.getLogger("jagsi.bridge")

# Imported lazily so the API still starts when scikit-learn or the artifact is
# missing; the bridge then runs in store-only mode.
_SCHEMA_IMPORT_ERROR: Optional[Exception] = None
try:
    from ml.schema import SAMPLE_RATE_HZ, WINDOW_SIZE
except Exception as exc:  # pragma: no cover - exercised only on a broken install
    SAMPLE_RATE_HZ, WINDOW_SIZE = 10, 30
    _SCHEMA_IMPORT_ERROR = exc


class WindowRejected(Exception):
    """A motion window does not match the contract the model was trained on."""


def parse_window(msg: Dict[str, Any]) -> List[Any]:
    """Validates a ``motion`` payload and returns it as a list of AccelSample.

    Every rejection here is a window the model must not score. Scoring a window
    with the wrong length or broken 10 Hz spacing does not fail loudly, it just
    returns a confident wrong answer, which is worse.
    """
    from ml.schema import AccelSample  # local import: see module docstring

    rate = msg.get("sample_rate_hz")
    if rate != SAMPLE_RATE_HZ:
        raise WindowRejected(f"sample_rate_hz is {rate!r}, model needs {SAMPLE_RATE_HZ}")

    size = msg.get("window_size")
    if size != WINDOW_SIZE:
        raise WindowRejected(f"window_size is {size!r}, model needs {WINDOW_SIZE}")

    rows = msg.get("s")
    if not isinstance(rows, list) or len(rows) != WINDOW_SIZE:
        got = len(rows) if isinstance(rows, list) else type(rows).__name__
        raise WindowRejected(f"'s' must hold {WINDOW_SIZE} rows, got {got}")

    dropped = msg.get("dropped") or 0
    if dropped:
        raise WindowRejected(f"device reported {dropped} dropped samples, spacing is not 10 Hz")

    samples = []
    for i, row in enumerate(rows):
        if not isinstance(row, (list, tuple)) or len(row) != 6:
            raise WindowRejected(f"row {i} must be [ax, ay, az, gx, gy, gz]")
        try:
            ax, ay, az, gx, gy, gz = (float(x) for x in row)
        except (TypeError, ValueError) as exc:
            raise WindowRejected(f"row {i} holds a non-numeric value") from exc
        samples.append(AccelSample(ax=ax, ay=ay, az=az, gx=gx, gy=gy, gz=gz))
    return samples


def _parse_iso(ts: str) -> datetime:
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


class Bridge:
    """Owns the MQTT connection and routes messages into the store."""

    def __init__(
        self,
        settings: Settings,
        store: Store,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self._on_event = on_event
        self._loop: Optional[AbstractEventLoop] = None
        self._classifier = None
        self._lock = threading.Lock()
        self._last_ml_alert_at: Dict[str, datetime] = {}

        self.stats = {
            "connected": False,
            "telemetry": 0,
            "motion_scored": 0,
            "motion_rejected": 0,
            "events": 0,
            "alerts_ml": 0,
            "alerts_device": 0,
            "last_reject_reason": None,
            "classifier_loaded": False,
            "threshold": None,
        }

        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"jagsi-bridge-{int(datetime.now().timestamp())}",
        )
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message

    # -- lifecycle -----------------------------------------------------------
    def attach_loop(self, loop: AbstractEventLoop) -> None:
        """Remembers the event loop so callbacks can push SSE updates to it."""
        self._loop = loop

    def load_classifier(self) -> None:
        if not self.settings.enable_classifier:
            log.info("classifier disabled by configuration, running in store-only mode")
            return
        if _SCHEMA_IMPORT_ERROR is not None:
            log.warning("ml package unavailable (%s), running in store-only mode", _SCHEMA_IMPORT_ERROR)
            return
        try:
            from ml.inference import FallClassifier

            self._classifier = FallClassifier.load(self.settings.model_path)
            if self.settings.fall_threshold is not None:
                log.warning(
                    "overriding the stored decision threshold %.3f with %.3f",
                    self._classifier.threshold,
                    self.settings.fall_threshold,
                )
                self._classifier.threshold = self.settings.fall_threshold
            self.stats["classifier_loaded"] = True
            self.stats["threshold"] = self._classifier.threshold
            log.info(
                "fall classifier loaded from %s (threshold %.3f)",
                self.settings.model_path,
                self._classifier.threshold,
            )
        except Exception as exc:
            log.warning("could not load the classifier (%s), running in store-only mode", exc)

    def start(self) -> None:
        self.load_classifier()
        log.info("connecting to %s:%s", self.settings.mqtt_host, self.settings.mqtt_port)
        self.client.connect_async(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=30)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.loop_stop()
        try:
            self.client.disconnect()
        except Exception:
            pass

    # -- MQTT callbacks ------------------------------------------------------
    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        if reason_code != 0:
            log.error("connect refused: %s", reason_code)
            return
        self.stats["connected"] = True
        # Deliberately not the documented 'jagsi/abal/v1/+/#' wildcard: it also
        # matches the cmd topic this bridge publishes to, so the broker would
        # hand every ack_alert straight back to us.
        topics = self.settings.subscribe_topics
        client.subscribe(topics)
        log.info("subscribed to %s", ", ".join(t for t, _ in topics))

    def _on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        self.stats["connected"] = False
        log.warning("disconnected (%s), paho will retry", reason_code)

    def _on_message(self, client, userdata, message: mqtt.MQTTMessage) -> None:
        try:
            payload = json.loads(message.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            log.warning("ignoring unparseable message on %s: %s", message.topic, exc)
            return
        if not isinstance(payload, dict) or "device_id" not in payload:
            log.warning("ignoring message without device_id on %s", message.topic)
            return

        suffix = message.topic.rsplit("/", 1)[-1]
        try:
            if suffix == "telemetry":
                self._handle_telemetry(payload)
            elif suffix == "motion":
                self._handle_motion(payload)
            elif suffix == "event":
                self._handle_event(payload)
            elif suffix == "status":
                self._handle_status(payload)
        except Exception:
            log.exception("handler for %s failed", message.topic)

    # -- handlers ------------------------------------------------------------
    def _handle_telemetry(self, msg: Dict[str, Any]) -> None:
        self.store.insert_telemetry(msg)
        self.stats["telemetry"] += 1
        self._broadcast({"type": "telemetry", "data": self.store.latest_telemetry(msg["device_id"])})

    def _handle_status(self, msg: Dict[str, Any]) -> None:
        self.store.upsert_device(msg)
        self._broadcast({"type": "status", "data": self.store.device(msg["device_id"])})

    def _handle_event(self, msg: Dict[str, Any]) -> None:
        """A device-rule alert: the 2.5 g threshold in the firmware fired."""
        self.stats["events"] += 1
        event_id = msg.get("event_id")
        if not event_id:
            log.warning("event without event_id, ignoring")
            return

        is_new = self.store.insert_alert(
            alert_id=event_id,
            device_id=msg["device_id"],
            alert_type=msg.get("alert_type", "fall_detected"),
            source="device_rule",
            timestamp=msg.get("ts"),
            accel_peak_g=msg.get("accel_peak_g"),
            vitals=msg.get("vitals"),
        )
        if is_new:
            self.stats["alerts_device"] += 1
            self._broadcast({"type": "alert", "data": self._alert_view(event_id)})

        # Acknowledge either way. A re-send means our previous ack was lost, and
        # leaving it unacked makes the device burn its five attempts for nothing.
        self.send_command(msg["device_id"], {"cmd": "ack_alert", "event_id": event_id})

    def _handle_motion(self, msg: Dict[str, Any]) -> None:
        if self._classifier is None:
            return
        try:
            samples = parse_window(msg)
        except WindowRejected as exc:
            self.stats["motion_rejected"] += 1
            self.stats["last_reject_reason"] = str(exc)
            log.warning("motion window rejected: %s", exc)
            return

        result = self._classifier.predict_window(samples)
        self.stats["motion_scored"] += 1
        if not result.is_fall:
            return

        device_id = msg["device_id"]
        if not self._should_raise_ml_alert(device_id):
            return

        alert_id = f"ml-{device_id}-{msg.get('seq', 0)}-{int(datetime.now().timestamp())}"
        latest = self.store.latest_telemetry(device_id) or {}
        created = self.store.insert_alert(
            alert_id=alert_id,
            device_id=device_id,
            alert_type="fall_detected",
            source="ml",
            timestamp=msg.get("ts"),
            confidence=round(result.confidence, 4),
            accel_peak_g=latest.get("accel_peak_g"),
            vitals={
                "heart_rate": latest.get("heart_rate"),
                "spo2": latest.get("spo2"),
                "body_temperature": latest.get("body_temperature"),
            },
        )
        if created:
            self.stats["alerts_ml"] += 1
            with self._lock:
                self._last_ml_alert_at[device_id] = datetime.now(timezone.utc)
            log.info("ML fall alert for %s, confidence %.3f", device_id, result.confidence)
            self._broadcast({"type": "alert", "data": self._alert_view(alert_id)})

    def _should_raise_ml_alert(self, device_id: str) -> bool:
        """Suppresses duplicates from the device rule and from overlapping windows."""
        now = datetime.now(timezone.utc)

        with self._lock:
            last_ml = self._last_ml_alert_at.get(device_id)
        if last_ml and now - last_ml < timedelta(seconds=self.settings.ml_alert_cooldown_seconds):
            log.debug("ML alert for %s suppressed: still in cooldown", device_id)
            return False

        # One fall sits in three overlapping windows and also trips the device
        # rule. Without this the caregiver gets four alerts for one event.
        last_device = self.store.last_device_alert_at(device_id, "fall_detected")
        if last_device:
            try:
                if now - _parse_iso(last_device) < timedelta(seconds=self.settings.duplicate_window_seconds):
                    log.info("ML alert for %s suppressed: device rule already reported it", device_id)
                    return False
            except ValueError:
                pass
        return True

    # -- outbound ------------------------------------------------------------
    def send_command(self, device_id: str, command: Dict[str, Any]) -> bool:
        topic = self.settings.topic("cmd", device_id)
        info = self.client.publish(topic, json.dumps(command), qos=1)
        ok = info.rc == mqtt.MQTT_ERR_SUCCESS
        if not ok:
            log.warning("could not publish %s to %s (rc=%s)", command, topic, info.rc)
        return ok

    # -- helpers -------------------------------------------------------------
    def _alert_view(self, alert_id: str) -> Optional[Dict[str, Any]]:
        for alert in self.store.recent_alerts(limit=25):
            if alert["alert_id"] == alert_id:
                return alert
        return None

    def _broadcast(self, event: Dict[str, Any]) -> None:
        """Hands an update to the event loop for the SSE subscribers."""
        if self._on_event is None or self._loop is None:
            return
        event.setdefault("at", utcnow())
        try:
            self._loop.call_soon_threadsafe(self._on_event, event)
        except RuntimeError:
            pass  # loop is shutting down
