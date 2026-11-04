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
"""

from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Set

from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from .bridge import Bridge
from .config import settings
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


bridge = Bridge(settings, store, on_event=_publish)


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
        "broker": f"{settings.mqtt_host}:{settings.mqtt_port}",
        "subscribed_to": [t for t, _ in settings.subscribe_topics],
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
        raise HTTPException(status_code=503, detail="broker unreachable, command not sent")
    return {"device_id": device_id, "sent": command}


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
