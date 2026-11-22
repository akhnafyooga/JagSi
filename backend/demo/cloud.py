"""Supabase cloud mirror and trend-inference API (issue #21).

Implements sections 10 and 11 of docs/wokwi-team-requirements.md:

* R07  telemetry, alerts and model results are persisted in Supabase PostgreSQL
* R08  synchronization resumes after a cloud outage, in batches, from a cursor
* R09  trend guidance is served from stored readings and traces back to them
* R12  the database URI stays in backend environment variables

Two processes share this module:

    python -m demo.serve      the existing API plus the routes below (terminal A)
    python -m demo.cloud      the mirror worker (terminal B)

The MQTT bridge keeps writing to SQLite exactly as before. The worker reads
committed SQLite rows and copies them to the cloud, so a slow or unreachable
cloud can never block 10 Hz sampling or alert delivery. Each batch and the
cursor that records it are written in one PostgreSQL transaction: a failed
batch rolls back completely and the next attempt starts from the same row.

Routes (added to app.main):

    GET /api/devices/{id}/progress        trend-model result over the last 60 cloud readings
    GET /api/devices/{id}/cloud-history   readings as stored in the cloud
    GET /api/cloud/status                 row counts and the mirror cursor

Everything is read from the environment at call time, not import time, so the
API still starts (and its existing tests still run) when the cloud is not
configured. The cloud routes then answer 503 with the reason.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import os
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import APIRouter, HTTPException, Query

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env.demo"

log = logging.getLogger("jagsi.cloud")

# Rows copied per transaction. Big enough to catch up quickly after an outage
# (a minute offline at one reading every 2 s is 30 rows), small enough to stay
# well inside the 10 s statement timeout on the free tier.
BATCH_SIZE = 200
STATEMENT_TIMEOUT = "10s"

# The trend model analyses this many consecutive readings (about two minutes at
# the firmware's 2 s telemetry interval).
WINDOW_ROWS = 60
MIN_SPAN_S, MAX_SPAN_S = 100.0, 180.0
MAX_GAP_S = 6.0
# Below this the endpoint says "uncertain" instead of giving guidance.
MIN_CONFIDENCE = 0.65

# Reviewed, deterministic caregiver wording (section 11). It describes the
# simulated input pattern and asks for a check; it never diagnoses.
GUIDANCE = {
    "stable": "Pola simulasi relatif stabil pada jendela ini. Lanjutkan pemantauan.",
    "rising_hr": "Detak jantung simulasi meningkat. Periksa aktivitas dan konteks pembacaan.",
    "falling_spo2": "SpO2 simulasi menurun. Periksa pembacaan dan tindak lanjuti sesuai prosedur tim.",
    "rising_temperature": "Suhu simulasi meningkat. Periksa pembacaan dan pantau perubahan berikutnya.",
}
UNCERTAIN_GUIDANCE = "Pola belum pasti. Periksa data dan lanjutkan pemantauan."


def load_env_file() -> None:
    """Loads backend/.env.demo without overriding variables already set.

    Tests set JAGSI_SKIP_ENV_FILE so a developer's real credentials can never
    leak into a test run.
    """
    if os.getenv("JAGSI_SKIP_ENV_FILE"):
        return
    try:
        from dotenv import load_dotenv
    except ImportError:  # python-dotenv is in requirements-demo.txt only
        return
    load_dotenv(ENV_FILE, override=False)


load_env_file()


# -- configuration -------------------------------------------------------------
class CloudNotConfigured(RuntimeError):
    """JAGSI_CLOUD_DSN or JAGSI_SOURCE_ID is missing or malformed."""


class LocalDatabaseMissing(RuntimeError):
    """The backend has not created its SQLite file yet."""


class SourceCollision(RuntimeError):
    """The cloud cursor for this source ID belongs to a different SQLite file.

    Happens when two laptops share one JAGSI_SOURCE_ID, or when the SQLite file
    was deleted or replaced but the UUID was kept. Mirroring would mix two
    unrelated row-ID sequences under one key, so the worker stops instead.
    """


class MirrorBusy(RuntimeError):
    """Another worker is mirroring the same source ID right now."""


def _resolve(path: str) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else (BACKEND_DIR / candidate)


@dataclass(frozen=True)
class CloudConfig:
    dsn: str
    source_id: str
    device_id: str
    db_path: Path
    model_path: Path
    max_age_s: float

    @classmethod
    def from_env(cls) -> "CloudConfig":
        dsn = os.getenv("JAGSI_CLOUD_DSN", "").strip()
        raw_source = os.getenv("JAGSI_SOURCE_ID", "").strip()
        if not dsn or not raw_source:
            raise CloudNotConfigured(
                "Set JAGSI_CLOUD_DSN and JAGSI_SOURCE_ID in backend/.env.demo "
                "(see .env.demo.example and docs/cloud-inference.md)"
            )
        try:
            source = str(uuid.UUID(raw_source))
        except ValueError as exc:
            raise CloudNotConfigured("JAGSI_SOURCE_ID must be a UUID") from exc
        return cls(
            dsn=dsn,
            source_id=source,
            device_id=os.getenv("JAGSI_DEVICE_ID", "jagsi-watch-01"),
            db_path=_resolve(os.getenv("JAGSI_DB_PATH", "data/jagsi.db")),
            model_path=_resolve(
                os.getenv("JAGSI_TREND_MODEL", "demo/artifacts/trend_model.joblib")
            ),
            max_age_s=float(os.getenv("JAGSI_PROGRESS_MAX_AGE_S", "10")),
        )


def connect(cfg: CloudConfig):
    """Opens one PostgreSQL connection with the demo's timeouts.

    prepare_threshold=None keeps psycopg from using server-side prepared
    statements, which Supabase's transaction pooler (port 6543) does not
    support. The session pooler works either way.
    """
    import psycopg  # imported here so the API starts without the demo extras

    conn = psycopg.connect(cfg.dsn, connect_timeout=5, prepare_threshold=None)
    conn.execute(f"set statement_timeout = '{STATEMENT_TIMEOUT}'")
    return conn


def _jsonb(value: Dict[str, Any]):
    from psycopg.types.json import Jsonb

    return Jsonb(value)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


_UPSERT = """
insert into public.jagsi_demo_records
    (source_id, kind, record_id, device_id, observed_at, payload)
values (%s, %s, %s, %s, %s, %s)
on conflict (source_id, kind, record_id) do update set
    payload = excluded.payload, observed_at = excluded.observed_at
where public.jagsi_demo_records.payload is distinct from excluded.payload
"""


def _put(conn, cfg: CloudConfig, kind: str, record_id: Any, observed_at, payload) -> int:
    """Inserts or updates one record. Returns 1 if a row changed, 0 if identical."""
    if isinstance(observed_at, str):
        observed_at = _parse_time(observed_at)
    cur = conn.execute(
        _UPSERT,
        (cfg.source_id, kind, str(record_id), cfg.device_id, observed_at, _jsonb(payload)),
    )
    return cur.rowcount


# -- mirror worker ---------------------------------------------------------------
@dataclass
class MirrorResult:
    telemetry: int
    alerts_changed: int
    last_id: int

    @property
    def caught_up(self) -> bool:
        return self.telemetry < BATCH_SIZE


def _telemetry_payload(row: sqlite3.Row) -> Dict[str, Any]:
    value = dict(row)
    value["simulated"] = bool(value.get("simulated"))
    return value


def _alert_payload(row: sqlite3.Row) -> Dict[str, Any]:
    value = dict(row)
    raw = value.pop("vitals_json", None)
    try:
        value["vitals"] = json.loads(raw) if raw else None
    except json.JSONDecodeError:
        value["vitals"] = None
    # Every reading in the selected demo comes from Wokwi or a replay script.
    value["simulated"] = True
    return value


def _fingerprint(local: sqlite3.Connection, device_id: str) -> Optional[str]:
    """Identifies one SQLite file by its first telemetry row for the device.

    The first row never changes once written, so the same file always gives the
    same value, and a new or different file almost certainly gives another one.
    """
    first = local.execute(
        "select telemetry_id, received_at, seq, uptime_ms from telemetry_data "
        "where device_id=? order by telemetry_id limit 1",
        (device_id,),
    ).fetchone()
    if first is None:
        return None
    text = "|".join(str(first[k]) for k in ("telemetry_id", "received_at", "seq", "uptime_ms"))
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def _advisory_key(source_id: str) -> int:
    # Postgres advisory locks take a signed 64-bit key.
    return uuid.UUID(source_id).int & 0x7FFF_FFFF_FFFF_FFFF


def mirror_once(
    cfg: Optional[CloudConfig] = None,
    connector: Callable[[CloudConfig], Any] = connect,
    batch_size: int = BATCH_SIZE,
) -> MirrorResult:
    """Copies the next batch of committed SQLite rows to the cloud.

    One call is one PostgreSQL transaction: the telemetry batch, every alert
    snapshot that changed, and the advanced cursor commit together or not at
    all. Calling it again after any failure is always safe.
    """
    cfg = cfg or CloudConfig.from_env()
    if not cfg.db_path.exists():
        raise LocalDatabaseMissing(
            f"Start the backend first; SQLite is missing at {cfg.db_path}"
        )

    with connector(cfg) as cloud:
        locked = cloud.execute(
            "select pg_try_advisory_xact_lock(%s)", (_advisory_key(cfg.source_id),)
        ).fetchone()[0]
        if not locked:
            raise MirrorBusy(f"another worker is mirroring source {cfg.source_id}")

        saved = cloud.execute(
            "select payload from public.jagsi_demo_records "
            "where source_id=%s and kind='cursor' and record_id='telemetry'",
            (cfg.source_id,),
        ).fetchone()
        cursor = int(saved[0]["last_id"]) if saved else 0
        saved_print = saved[0].get("db_fingerprint") if saved else None

        local = sqlite3.connect(f"file:{cfg.db_path.as_posix()}?mode=ro", uri=True, timeout=5)
        local.row_factory = sqlite3.Row
        try:
            fingerprint = _fingerprint(local, cfg.device_id)
            newest = local.execute(
                "select coalesce(max(telemetry_id), 0) from telemetry_data where device_id=?",
                (cfg.device_id,),
            ).fetchone()[0]
            if saved_print and fingerprint and saved_print != fingerprint:
                raise SourceCollision(
                    f"source {cfg.source_id} was mirrored from a different SQLite file. "
                    "Use a new JAGSI_SOURCE_ID for this database."
                )
            if cursor > newest:
                raise SourceCollision(
                    f"cloud cursor is at telemetry {cursor} but this SQLite file ends at "
                    f"{newest}. It was replaced or reset; use a new JAGSI_SOURCE_ID."
                )
            rows = local.execute(
                "select * from telemetry_data where telemetry_id>? and device_id=? "
                "order by telemetry_id limit ?",
                (cursor, cfg.device_id, batch_size),
            ).fetchall()
            alerts = local.execute(
                "select * from alert_event where device_id=?", (cfg.device_id,)
            ).fetchall()
        finally:
            local.close()

        for row in rows:
            _put(cloud, cfg, "telemetry", row["telemetry_id"], row["received_at"],
                 _telemetry_payload(row))
        # All alert snapshots are compared each pass so an acknowledgment made
        # after the first copy reaches the cloud too. Unchanged rows are skipped
        # by the upsert's WHERE clause, so this costs no writes when idle.
        changed = sum(
            _put(cloud, cfg, "alert", row["alert_id"], row["received_at"], _alert_payload(row))
            for row in alerts
        )
        last_id = rows[-1]["telemetry_id"] if rows else cursor
        if rows or (fingerprint and saved_print is None):
            _put(cloud, cfg, "cursor", "telemetry", datetime.now(timezone.utc),
                 {"last_id": last_id, "db_fingerprint": fingerprint,
                  "updated_at": datetime.now(timezone.utc).isoformat()})
        return MirrorResult(telemetry=len(rows), alerts_changed=changed, last_id=last_id)


def run_worker(once: bool = False) -> int:
    """Mirror loop for terminal B. Returns a process exit code."""
    cfg = CloudConfig.from_env()
    log.info("mirroring %s for %s into source %s", cfg.db_path, cfg.device_id, cfg.source_id)
    backoff = 5.0
    while True:
        try:
            result = mirror_once(cfg)
            if result.telemetry or result.alerts_changed:
                log.info("mirrored telemetry=%s alerts_changed=%s cursor=%s",
                         result.telemetry, result.alerts_changed, result.last_id)
            backoff = 5.0
            if once:
                return 0
            time.sleep(2 if result.caught_up else 0.1)
        except KeyboardInterrupt:
            return 0
        except (SourceCollision, CloudNotConfigured) as exc:
            log.error("%s", exc)
            return 2
        except (LocalDatabaseMissing, MirrorBusy) as exc:
            log.warning("%s; retrying in 5 s", exc)
            if once:
                return 1
            time.sleep(5)
        except Exception:
            # Network loss, paused project, bad password... SQLite keeps every
            # row, so nothing is lost: retry with a growing pause.
            log.exception("sync failed; local rows are kept and will be retried in %.0f s", backoff)
            if once:
                return 1
            time.sleep(backoff)
            backoff = min(backoff * 2, 60.0)


# -- trend model -----------------------------------------------------------------
class TrendModelUnavailable(RuntimeError):
    pass


_model_lock = threading.Lock()
_model_cache: Dict[str, Tuple[float, Dict[str, Any], str]] = {}


def load_trend_model(path: Path) -> Tuple[Dict[str, Any], str]:
    """Loads (and caches until the file changes) the #20 trend artifact."""
    from demo.train_trends import FEATURES

    try:
        mtime = path.stat().st_mtime
    except FileNotFoundError as exc:
        raise TrendModelUnavailable(
            f"trend model not found at {path}; run python -m demo.train_trends"
        ) from exc
    with _model_lock:
        cached = _model_cache.get(str(path))
        if cached and cached[0] == mtime:
            return cached[1], cached[2]
        import joblib

        try:
            artifact = joblib.load(path)
        except Exception as exc:
            raise TrendModelUnavailable(f"trend model at {path} could not be loaded") from exc
        if not isinstance(artifact, dict) or "model" not in artifact:
            raise TrendModelUnavailable("trend artifact has no model")
        if list(artifact.get("features", [])) != FEATURES or artifact.get("rows") != WINDOW_ROWS:
            raise TrendModelUnavailable(
                "trend artifact was trained on a different feature contract"
            )
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        _model_cache[str(path)] = (mtime, artifact, digest)
        return artifact, digest


def _finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def assess(rows: List[Dict[str, Any]], cfg: CloudConfig,
           now: Optional[datetime] = None) -> Dict[str, Any]:
    """Checks a window of cloud readings, oldest first, before any prediction.

    Returns a result with state "ok" when the model may run, otherwise the
    labelled reason it may not. Never predicts on incomplete, old or irregular
    input (definition of done, section 14).
    """
    now = now or datetime.now(timezone.utc)
    if len(rows) < WINDOW_ROWS:
        return {"state": "insufficient_data", "count": len(rows), "required": WINDOW_ROWS}
    times = [_parse_time(r["received_at"]) for r in rows]
    age = (now - times[-1]).total_seconds()
    if age > cfg.max_age_s or age < -5:
        return {"state": "stale", "age_seconds": round(age, 1),
                "last_reading_at": times[-1].isoformat()}
    span = (times[-1] - times[0]).total_seconds()
    gaps = [(b - a).total_seconds() for a, b in zip(times, times[1:])]
    if not MIN_SPAN_S <= span <= MAX_SPAN_S or min(gaps) <= 0 or max(gaps) > MAX_GAP_S:
        return {"state": "irregular_sampling", "span_seconds": span,
                "max_gap_seconds": max(gaps), "min_gap_seconds": min(gaps)}
    values = [[r.get("heart_rate"), r.get("spo2"), r.get("body_temperature")] for r in rows]
    if not all(_finite(v) for sample in values for v in sample):
        missing = sum(1 for sample in values if not all(_finite(v) for v in sample))
        return {"state": "missing_values", "rows_with_missing_values": missing}
    return {"state": "ok", "times": times, "values": values, "span": span}


def predict(rows: List[Dict[str, Any]], cfg: CloudConfig,
            now: Optional[datetime] = None) -> Dict[str, Any]:
    """Runs the trend model on 60 cloud readings (oldest first)."""
    import numpy as np
    from demo.train_trends import features

    checked = assess(rows, cfg, now)
    simulated = all(bool(r.get("simulated")) for r in rows) if rows else True
    if checked["state"] != "ok":
        return {**checked, "simulated": simulated}

    artifact, digest = load_trend_model(cfg.model_path)
    values = checked["values"]
    times = checked["times"]
    probabilities = artifact["model"].predict_proba([features(values)])[0]
    index = int(probabilities.argmax())
    label = str(artifact["model"].classes_[index])
    confidence = float(probabilities[index])
    ready = confidence >= MIN_CONFIDENCE
    array = np.asarray(values, dtype=float)
    channels = ("heart_rate", "spo2", "body_temperature")
    return {
        "state": "ready" if ready else "uncertain",
        "label": label,
        "confidence": round(confidence, 4),
        "probabilities": {
            str(c): round(float(p), 4) for c, p in zip(artifact["model"].classes_, probabilities)
        },
        "guidance": GUIDANCE[label] if ready else UNCERTAIN_GUIDANCE,
        "model_version": artifact.get("version"),
        "model_sha256": digest,
        "simulated": simulated,
        "generated_at": (now or datetime.now(timezone.utc)).isoformat(),
        # Traceability (R09): the exact stored rows this answer was computed from.
        "from": times[0].isoformat(),
        "to": times[-1].isoformat(),
        "telemetry_ids": [rows[0]["telemetry_id"], rows[-1]["telemetry_id"]],
        "sample_count": len(rows),
        "span_seconds": checked["span"],
        "stats": {
            "first_10_mean": dict(zip(channels, np.round(array[:10].mean(axis=0), 2).tolist())),
            "last_10_mean": dict(zip(channels, np.round(array[-10:].mean(axis=0), 2).tolist())),
        },
    }


# -- API routes ------------------------------------------------------------------
router = APIRouter(tags=["cloud"])


def _config_or_503() -> CloudConfig:
    try:
        return CloudConfig.from_env()
    except CloudNotConfigured as exc:
        raise HTTPException(503, f"Cloud storage is not configured: {exc}") from exc


def _check_device(device_id: str, cfg: CloudConfig) -> None:
    if device_id != cfg.device_id:
        raise HTTPException(404, "Unknown demo device")


def _latest_telemetry(conn, cfg: CloudConfig, limit: int) -> List[Dict[str, Any]]:
    records = conn.execute(
        "select payload from public.jagsi_demo_records "
        "where source_id=%s and kind='telemetry' and device_id=%s "
        "order by observed_at desc, record_id::bigint desc limit %s",
        (cfg.source_id, cfg.device_id, limit),
    ).fetchall()
    return [r[0] for r in reversed(records)]


@router.get("/api/devices/{device_id}/progress")
def progress(device_id: str) -> Dict[str, Any]:
    cfg = _config_or_503()
    _check_device(device_id, cfg)
    try:
        with connect(cfg) as cloud:
            rows = _latest_telemetry(cloud, cfg, WINDOW_ROWS)
            result = predict(rows, cfg)
            if result["state"] in ("ready", "uncertain"):
                identity = f"{result['telemetry_ids'][1]}-{result['model_version']}"
                _put(cloud, cfg, "analysis", identity, result["to"], result)
            return result
    except TrendModelUnavailable as exc:
        log.warning("%s", exc)
        raise HTTPException(503, f"Trend model unavailable: {exc}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("cloud progress unavailable")
        raise HTTPException(503, "Cloud data unavailable") from exc


@router.get("/api/devices/{device_id}/cloud-history")
def cloud_history(device_id: str, limit: int = Query(120, ge=1, le=1000)) -> Dict[str, Any]:
    cfg = _config_or_503()
    _check_device(device_id, cfg)
    try:
        with connect(cfg) as cloud:
            points = _latest_telemetry(cloud, cfg, limit)
    except Exception as exc:
        log.exception("cloud history unavailable")
        raise HTTPException(503, "Cloud history unavailable") from exc
    return {"device_id": device_id, "simulated": all(p.get("simulated") for p in points),
            "count": len(points), "points": points}


@router.get("/api/cloud/status")
def cloud_status() -> Dict[str, Any]:
    cfg = _config_or_503()
    try:
        with connect(cfg) as cloud:
            counts = dict(cloud.execute(
                "select kind, count(*) from public.jagsi_demo_records "
                "where source_id=%s group by kind", (cfg.source_id,)).fetchall())
            cursor = cloud.execute(
                "select payload from public.jagsi_demo_records "
                "where source_id=%s and kind='cursor' and record_id='telemetry'",
                (cfg.source_id,)).fetchone()
            newest = cloud.execute(
                "select max(observed_at) from public.jagsi_demo_records "
                "where source_id=%s and kind='telemetry'", (cfg.source_id,)).fetchone()[0]
    except Exception as exc:
        log.exception("cloud status unavailable")
        raise HTTPException(503, "Cloud storage unreachable") from exc
    return {
        "source_id": cfg.source_id,
        "device_id": cfg.device_id,
        "counts": {k: counts.get(k, 0) for k in ("telemetry", "alert", "analysis")},
        "cursor": cursor[0] if cursor else None,
        "newest_telemetry_at": newest.isoformat() if newest else None,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Mirror backend SQLite rows to Supabase")
    parser.add_argument("--once", action="store_true", help="mirror one batch and exit")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    try:
        return run_worker(once=args.once)
    except CloudNotConfigured as exc:
        log.error("%s", exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
