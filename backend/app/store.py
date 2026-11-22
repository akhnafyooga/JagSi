"""SQLite persistence for telemetry and alerts.

Sprint 2 stand-in for the cloud database. The table and column names follow the
project ERD so that moving to Azure SQL later is a connection-string change and a
dialect pass, not a redesign.

Thread safety: the MQTT client calls ``insert_*`` from its own network thread while
FastAPI reads from the event loop thread, so every call takes a short-lived
connection guarded by one lock. At this project's volume (roughly one telemetry row
every two seconds per device) that is far simpler than a pool and fast enough.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS wearable_device (
    device_id       TEXT PRIMARY KEY,
    state           TEXT,
    fw              TEXT,
    battery_level   INTEGER,
    ip              TEXT,
    interval_ms     INTEGER,
    motion_enabled  INTEGER,
    last_seen       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS telemetry_data (
    telemetry_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id         TEXT NOT NULL,
    seq               INTEGER,
    timestamp         TEXT NOT NULL,   -- device clock, or receive time if unsynced
    received_at       TEXT NOT NULL,   -- server clock, always set
    ts_source         TEXT NOT NULL,   -- 'device' | 'server'
    uptime_ms         INTEGER,
    heart_rate        INTEGER,
    spo2              REAL,
    body_temperature  REAL,
    accel_x           REAL,
    accel_y           REAL,
    accel_z           REAL,
    accel_peak_g      REAL,
    battery_level     INTEGER,
    simulated         INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_telemetry_device_time
    ON telemetry_data (device_id, received_at DESC);

CREATE TABLE IF NOT EXISTS alert_event (
    alert_id     TEXT PRIMARY KEY,     -- event_id from the device, or ml-... from the backend
    device_id    TEXT NOT NULL,
    alert_type   TEXT NOT NULL,        -- 'fall_detected' | 'manual_sos'
    source       TEXT NOT NULL,        -- 'device_rule' | 'ml'
    status       TEXT NOT NULL,        -- 'unresolved' | 'acknowledged'
    timestamp    TEXT NOT NULL,
    received_at  TEXT NOT NULL,
    confidence   REAL,                 -- ML only
    accel_peak_g REAL,
    vitals_json  TEXT,
    attempts     INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_alert_device_time
    ON alert_event (device_id, received_at DESC);
"""


def utcnow() -> str:
    """Server timestamp, ISO 8601 with a Z suffix, second resolution."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Store:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._lock = threading.Lock()
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # -- writes --------------------------------------------------------------
    def insert_telemetry(self, msg: Dict[str, Any]) -> None:
        """Stores one telemetry message.

        ``ts`` may be null when the device has not reached an NTP server yet. In
        that case the server's receive time is stored as the timestamp and
        ``ts_source`` records that it was substituted, so a later analysis does not
        mistake it for a device reading.
        """
        received = utcnow()
        device_ts = msg.get("ts")
        accel = msg.get("accel") or {}
        row = (
            msg["device_id"],
            msg.get("seq"),
            device_ts or received,
            received,
            "device" if device_ts else "server",
            msg.get("uptime_ms"),
            msg.get("heart_rate"),
            msg.get("spo2"),
            msg.get("body_temperature"),
            accel.get("x"),
            accel.get("y"),
            accel.get("z"),
            msg.get("accel_peak_g"),
            msg.get("battery_level"),
            1 if msg.get("sim") else 0,
        )
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO telemetry_data
                   (device_id, seq, timestamp, received_at, ts_source, uptime_ms,
                    heart_rate, spo2, body_temperature, accel_x, accel_y, accel_z,
                    accel_peak_g, battery_level, simulated)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                row,
            )

    def upsert_device(self, msg: Dict[str, Any]) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """INSERT INTO wearable_device
                       (device_id, state, fw, battery_level, ip, interval_ms,
                        motion_enabled, last_seen)
                   VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(device_id) DO UPDATE SET
                       state          = excluded.state,
                       fw             = COALESCE(excluded.fw, wearable_device.fw),
                       battery_level  = COALESCE(excluded.battery_level, wearable_device.battery_level),
                       ip             = COALESCE(excluded.ip, wearable_device.ip),
                       interval_ms    = COALESCE(excluded.interval_ms, wearable_device.interval_ms),
                       motion_enabled = COALESCE(excluded.motion_enabled, wearable_device.motion_enabled),
                       last_seen      = excluded.last_seen""",
                (
                    msg["device_id"],
                    msg.get("state"),
                    msg.get("fw"),
                    msg.get("battery_level"),
                    msg.get("ip"),
                    msg.get("interval_ms"),
                    None if msg.get("motion_enabled") is None else int(bool(msg["motion_enabled"])),
                    utcnow(),
                ),
            )

    def insert_alert(
        self,
        *,
        alert_id: str,
        device_id: str,
        alert_type: str,
        source: str,
        timestamp: Optional[str] = None,
        confidence: Optional[float] = None,
        accel_peak_g: Optional[float] = None,
        vitals: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Inserts an alert. Returns False if this ``alert_id`` was already stored.

        The device re-sends an unacknowledged event up to five times with the same
        ``event_id``, so duplicate inserts are the normal case, not an error.
        """
        received = utcnow()
        with self._lock, self._connect() as conn:
            existing = conn.execute(
                "SELECT 1 FROM alert_event WHERE alert_id = ?", (alert_id,)
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE alert_event SET attempts = attempts + 1 WHERE alert_id = ?",
                    (alert_id,),
                )
                return False
            conn.execute(
                """INSERT INTO alert_event
                       (alert_id, device_id, alert_type, source, status, timestamp,
                        received_at, confidence, accel_peak_g, vitals_json, attempts)
                   VALUES (?,?,?,?,'unresolved',?,?,?,?,?,1)""",
                (
                    alert_id,
                    device_id,
                    alert_type,
                    source,
                    timestamp or received,
                    received,
                    confidence,
                    accel_peak_g,
                    json.dumps(vitals) if vitals else None,
                ),
            )
            return True

    def acknowledge_alert(self, alert_id: str) -> bool:
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                "UPDATE alert_event SET status = 'acknowledged' WHERE alert_id = ?",
                (alert_id,),
            )
            return cur.rowcount > 0

    # -- reads ---------------------------------------------------------------
    def latest_telemetry(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM telemetry_data
                   WHERE device_id = ? ORDER BY received_at DESC, telemetry_id DESC
                   LIMIT 1""",
                (device_id,),
            ).fetchone()
        return dict(row) if row else None

    def telemetry_history(self, device_id: str, limit: int = 60) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM telemetry_data
                   WHERE device_id = ? ORDER BY telemetry_id DESC LIMIT ?""",
                (device_id, limit),
            ).fetchall()
        return [dict(r) for r in reversed(rows)]

    def recent_alerts(self, limit: int = 20, device_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM alert_event"
        params: List[Any] = []
        if device_id:
            sql += " WHERE device_id = ?"
            params.append(device_id)
        sql += " ORDER BY received_at DESC, rowid DESC LIMIT ?"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def last_device_alert_at(self, device_id: str, alert_type: str) -> Optional[str]:
        """Receive time of the newest device-rule alert, for duplicate suppression."""
        with self._connect() as conn:
            row = conn.execute(
                """SELECT received_at FROM alert_event
                   WHERE device_id = ? AND alert_type = ? AND source = 'device_rule'
                   ORDER BY received_at DESC LIMIT 1""",
                (device_id, alert_type),
            ).fetchone()
        return row["received_at"] if row else None

    def device(self, device_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM wearable_device WHERE device_id = ?", (device_id,)
            ).fetchone()
        return dict(row) if row else None

    def devices(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM wearable_device ORDER BY last_seen DESC"
            ).fetchall()
        return [dict(r) for r in rows]
