"""JagSi backend API.

Serves the caregiver dashboard with what the device actually sent, instead of the
mock data the frontend has been using since issue #12.

    uvicorn app.main:app --reload --port 8000     (run from backend/)

Endpoints
    GET  /api/health                             bridge and classifier status
    GET  /api/devices                            known devices and last contact
    GET  /api/devices/{id}/telemetry/latest      newest reading, dashboard-shaped
    GET  /api/devices/{id}/telemetry/history     recent readings for the charts
    GET  /api/alerts                             recent alerts, newest first
    POST /api/alerts/{alert_id}/ack              acknowledge, stops device re-sends
    POST /api/devices/{id}/command               ping / set_interval / set_motion
    GET  /api/stream                             server-sent events, live push

Week 7
    POST /api/ingest/eventgrid?key=...           Azure IoT Hub messages via Event Grid (#8)
    GET  /api/devices/{id}/summary               AI health summary, Gemini or rules (#10)
    POST /api/devices/{id}/chat                  caregiver question about the data (#10)
    GET  /api/recording                          labelled recording status (#9)
    POST /api/recording/start | /api/recording/stop
"""

from __future__ import annotations

import asyncio
import hmac
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set

from fastapi import Body, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .ai_summary import HealthAssistant
from .azure_iot import DirectMethodSender, EventGridError, parse_eventgrid
from .bridge import Bridge
from .config import settings
from .recorder import SUGGESTED_LABELS, MotionRecorder, RecordingError
from .store import Store, utcnow
from .vitals import telemetry_to_vitals

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("jagsi.api")

store = Store(settings.db_path)
_subscribers: Set[asyncio.Queue] = set()


def _publish(event: Dict[str, Any]) -> None:
    """Fans an update out to every open SSE connection.

    Runs on the event loop thread. A queue that is full means that client is not
    keeping up, so its oldest update is dropped rather than blocking the bridge.
    """
    for queue in list(_subscribers):
        if queue.full():
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            pass


def _command_sender() -> Optional[DirectMethodSender]:
    if not settings.azure:
        return None
    if not settings.azure_iothub_hostname or not settings.azure_service_key:
        raise RuntimeError(
            "JAGSI_INGEST=azure needs JAGSI_IOTHUB_HOSTNAME and JAGSI_IOTHUB_POLICY_KEY. "
            "See docs/azure-setup.md."
        )
    if not settings.eventgrid_key:
        raise RuntimeError(
            "JAGSI_INGEST=azure needs JAGSI_EVENTGRID_KEY, otherwise anyone who finds "
            "the webhook URL can post fake telemetry. See docs/azure-setup.md."
        )
    return DirectMethodSender(
        settings.azure_iothub_hostname, settings.azure_service_policy, settings.azure_service_key
    )


recorder = MotionRecorder(settings.recordings_dir)
bridge = Bridge(settings, store, on_event=_publish, command_sender=_command_sender(), recorder=recorder)
assistant = HealthAssistant(store, settings)


@asynccontextmanager
async def lifespan(app: FastAPI):
    bridge.attach_loop(asyncio.get_running_loop())
    bridge.start()
    try:
        yield
    finally:
        bridge.stop()


app = FastAPI(title="JagSi API", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "server_time": utcnow(),
        "ingest": settings.ingest_mode,
        "broker": (
            settings.azure_iothub_hostname
            if settings.azure
            else f"{settings.mqtt_host}:{settings.mqtt_port}"
        ),
        "subscribed_to": [] if settings.azure else [t for t, _ in settings.subscribe_topics],
        "ai_model": assistant.model_label,
        "recording": recorder.status()["active"],
        "subscribers": len(_subscribers),
        "bridge": bridge.stats,
    }


@app.get("/api/devices")
def devices() -> Dict[str, Any]:
    return {"devices": store.devices()}


@app.get("/api/devices/{device_id}/telemetry/latest")
def latest_telemetry(device_id: str) -> Dict[str, Any]:
    row = store.latest_telemetry(device_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                f"no telemetry stored for {device_id} yet. Check that the device is "
                "publishing and that /api/health shows the bridge connected."
            ),
        )
    device = store.device(device_id) or {}
    return {
        "device_id": device_id,
        "received_at": row["received_at"],
        "timestamp": row["timestamp"],
        "ts_source": row["ts_source"],
        "simulated": bool(row["simulated"]),
        "device_state": device.get("state"),
        "vitals": telemetry_to_vitals(row),
        "raw": row,
    }


@app.get("/api/devices/{device_id}/telemetry/history")
def telemetry_history(device_id: str, limit: int = 60) -> Dict[str, Any]:
    limit = max(1, min(limit, 500))
    rows = store.telemetry_history(device_id, limit)
    return {
        "device_id": device_id,
        "count": len(rows),
        "points": [
            {
                "received_at": r["received_at"],
                "heart_rate": r["heart_rate"],
                "spo2": r["spo2"],
                "body_temperature": r["body_temperature"],
                "accel_peak_g": r["accel_peak_g"],
            }
            for r in rows
        ],
    }


@app.get("/api/alerts")
def alerts(limit: int = 20, device_id: Optional[str] = None) -> Dict[str, Any]:
    limit = max(1, min(limit, 200))
    rows = store.recent_alerts(limit=limit, device_id=device_id)
    for row in rows:
        if row.get("vitals_json"):
            try:
                row["vitals"] = json.loads(row.pop("vitals_json"))
            except json.JSONDecodeError:
                row["vitals"] = None
        else:
            row.pop("vitals_json", None)
            row["vitals"] = None
    return {"alerts": rows}


@app.post("/api/alerts/{alert_id}/ack")
def acknowledge(alert_id: str) -> Dict[str, Any]:
    alerts_by_id = {a["alert_id"]: a for a in store.recent_alerts(limit=200)}
    alert = alerts_by_id.get(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"unknown alert {alert_id}")

    store.acknowledge_alert(alert_id)
    # Only a device-raised event needs the MQTT ack; an ML alert was never
    # waiting on one.
    sent = False
    if alert["source"] == "device_rule":
        sent = bridge.send_command(alert["device_id"], {"cmd": "ack_alert", "event_id": alert_id})
    _publish({"type": "alert_ack", "data": {"alert_id": alert_id}})
    return {"alert_id": alert_id, "status": "acknowledged", "ack_sent_to_device": sent}


_ALLOWED_COMMANDS = {"ping", "set_interval", "set_motion", "ack_alert"}


@app.post("/api/devices/{device_id}/command")
def send_command(device_id: str, command: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    cmd = command.get("cmd")
    if cmd not in _ALLOWED_COMMANDS:
        raise HTTPException(
            status_code=400,
            detail=f"cmd must be one of {sorted(_ALLOWED_COMMANDS)}, got {cmd!r}",
        )
    if not bridge.send_command(device_id, command):
        detail = (
            "device did not answer the direct method (offline or busy)"
            if settings.azure
            else "broker unreachable, command not sent"
        )
        raise HTTPException(status_code=503, detail=detail)
    return {"device_id": device_id, "sent": command}


# -- Azure IoT Hub via Event Grid (issue #8) ---------------------------------
@app.post("/api/ingest/eventgrid")
async def ingest_eventgrid(request: Request, key: str = Query("")) -> Any:
    """Receives IoT Hub events that Event Grid delivers to this webhook.

    Event Grid first sends a SubscriptionValidationEvent; answering with its
    validationCode proves we own the endpoint. After that, each POST is a batch
    of DeviceTelemetry / DeviceConnected / DeviceDisconnected events.
    """
    if not settings.azure:
        raise HTTPException(status_code=404, detail="Event Grid ingest is off (JAGSI_INGEST is not azure)")
    if not hmac.compare_digest(key, settings.eventgrid_key):
        raise HTTPException(status_code=401, detail="wrong or missing key")
    try:
        events = await request.json()
    except ValueError:
        raise HTTPException(status_code=400, detail="body is not JSON")
    try:
        delivery = parse_eventgrid(events)
    except EventGridError as exc:
        log.warning("Event Grid delivery refused: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc))

    if delivery.validation_code:
        log.info("Event Grid subscription validated")
        return {"validationResponse": delivery.validation_code}

    for kind, payload in delivery.messages:
        try:
            bridge.dispatch(kind, payload)
        except Exception:
            # One bad message must not make Event Grid retry the whole batch.
            log.exception("handler for %s from %s failed", kind, payload.get("device_id"))
    return {"accepted": len(delivery.messages), "skipped": delivery.skipped}


# -- AI health summary and chat (issue #10) ----------------------------------
@app.get("/api/devices/{device_id}/summary")
def health_summary(device_id: str, refresh: bool = False) -> Dict[str, Any]:
    return assistant.summary(device_id, force=refresh)


@app.post("/api/devices/{device_id}/chat")
def health_chat(device_id: str, body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
        raise HTTPException(status_code=400, detail="question must be a non-empty string")
    history = body.get("history") if isinstance(body.get("history"), list) else None
    return assistant.chat(device_id, question, history)


# -- labelled motion recording (issue #9) ------------------------------------
@app.get("/api/recording")
def recording_status() -> Dict[str, Any]:
    return {**recorder.status(), "suggested_labels": SUGGESTED_LABELS, "directory": settings.recordings_dir}


@app.post("/api/recording/start")
def recording_start(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    try:
        session = recorder.start(
            label=body.get("label", ""),
            subject=body.get("subject", ""),
            device_id=body.get("device_id"),
            note=str(body.get("note", ""))[:200],
        )
    except RecordingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return session


@app.post("/api/recording/stop")
def recording_stop() -> Dict[str, Any]:
    try:
        return recorder.stop()
    except RecordingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/api/stream")
async def stream(request: Request) -> StreamingResponse:
    """Server-sent events, so the dashboard updates without polling.

    SSE rather than WebSockets: the traffic is one-directional (device to
    caregiver), it survives proxies that mangle upgrades, and the browser
    reconnects on its own.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=50)
    _subscribers.add(queue)

    async def generator():
        try:
            yield f"event: hello\ndata: {json.dumps({'at': utcnow()})}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"   # keeps idle proxies from closing us
                    continue
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'], default=str)}\n\n"
        finally:
            _subscribers.discard(queue)

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
