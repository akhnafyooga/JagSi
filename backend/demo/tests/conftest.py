"""Fixtures for the cloud mirror and trend-inference tests (issue #21).

The cloud tests run against a real PostgreSQL server, because the behaviour
under test (upserts, transactions, rollbacks, advisory locks) is PostgreSQL's
own. Point JAGSI_TEST_PG_DSN at a disposable database, for example

    JAGSI_TEST_PG_DSN=postgresql://postgres:postgres@127.0.0.1:5432/postgres

CI starts a postgres:16 service for this. Without the variable those tests are
skipped and the rest still run. Never point it at the team's Supabase project:
every test empties the table.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Same isolation as app/tests/conftest.py, for when this folder runs alone.
_TMP = Path(tempfile.mkdtemp(prefix="jagsi-demo-test-"))
os.environ.setdefault("JAGSI_DB_PATH", str(_TMP / "api.db"))
os.environ.setdefault("JAGSI_MQTT_HOST", "127.0.0.1")
os.environ.setdefault("JAGSI_SKIP_ENV_FILE", "1")

import pytest  # noqa: E402

from app.store import Store  # noqa: E402
from demo.cloud import CloudConfig  # noqa: E402

SCHEMA = Path(__file__).resolve().parents[1] / "schema.sql"
DEVICE = "jagsi-watch-01"
PG_DSN = os.getenv("JAGSI_TEST_PG_DSN", "")


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LocalDB:
    """A backend SQLite file with rows written at chosen server times."""

    def __init__(self, path: Path) -> None:
        self.path = path
        Store(path)  # creates the real schema
        self._seq = 0

    def add_telemetry(self, received_at: datetime, hr=75, spo2=98.0, temp=36.6,
                      device=DEVICE, sim=1) -> int:
        self._seq += 1
        with sqlite3.connect(self.path) as conn:
            cur = conn.execute(
                """insert into telemetry_data (device_id, seq, timestamp, received_at,
                   ts_source, uptime_ms, heart_rate, spo2, body_temperature, accel_x,
                   accel_y, accel_z, accel_peak_g, battery_level, simulated)
                   values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (device, self._seq, _iso(received_at), _iso(received_at), "device",
                 self._seq * 2000, hr, spo2, temp, 0.0, 0.0, 1.0, 1.0, 90, sim),
            )
            return cur.lastrowid

    def add_series(self, values, end: datetime | None = None, step_s: float = 2.0):
        """values: list of (hr, spo2, temp); the last one is received at ``end``."""
        end = end or datetime.now(timezone.utc)
        count = len(values)
        return [self.add_telemetry(end - timedelta(seconds=step_s * (count - 1 - i)), *v)
                for i, v in enumerate(values)]

    def add_alert(self, alert_id: str, status="unresolved", when: datetime | None = None):
        when = when or datetime.now(timezone.utc)
        with sqlite3.connect(self.path) as conn:
            conn.execute(
                """insert into alert_event (alert_id, device_id, alert_type, source, status,
                   timestamp, received_at, confidence, accel_peak_g, vitals_json, attempts)
                   values (?,?,?,?,?,?,?,?,?,?,1)""",
                (alert_id, DEVICE, "manual_sos", "device_rule", status, _iso(when),
                 _iso(when), None, 1.0, '{"heart_rate": 80}'),
            )

    def set_alert_status(self, alert_id: str, status: str) -> None:
        with sqlite3.connect(self.path) as conn:
            conn.execute("update alert_event set status=? where alert_id=?", (status, alert_id))


@pytest.fixture
def local_db(tmp_path) -> LocalDB:
    return LocalDB(tmp_path / "jagsi.db")


@pytest.fixture(scope="session")
def pg_dsn() -> str:
    if not PG_DSN:
        pytest.skip("JAGSI_TEST_PG_DSN is not set; cloud tests need a disposable PostgreSQL")
    import psycopg

    with psycopg.connect(PG_DSN, autocommit=True) as conn:
        # Supabase creates these roles; a plain PostgreSQL does not.
        for role in ("anon", "authenticated"):
            conn.execute(
                f"do $$ begin create role {role} nologin; "
                f"exception when duplicate_object then null; end $$"
            )
        conn.execute("drop table if exists public.jagsi_demo_records")
        conn.execute(SCHEMA.read_text())
    return PG_DSN


@pytest.fixture
def cloud(pg_dsn):
    """An open autocommit connection to the emptied cloud table."""
    import psycopg

    with psycopg.connect(pg_dsn, autocommit=True) as conn:
        conn.execute("truncate public.jagsi_demo_records")
        yield conn


@pytest.fixture(scope="session")
def trend_model(tmp_path_factory) -> Path:
    """The #20 reference model, trained once into a temporary directory."""
    from demo.train_trends import train

    out = tmp_path_factory.mktemp("trend")
    train(out)
    return out / "trend_model.joblib"


@pytest.fixture
def cfg(pg_dsn, local_db, trend_model) -> CloudConfig:
    return CloudConfig(
        dsn=pg_dsn,
        source_id=str(uuid.uuid4()),
        device_id=DEVICE,
        db_path=local_db.path,
        model_path=trend_model,
        max_age_s=10.0,
    )


@pytest.fixture
def cloud_env(monkeypatch, cfg):
    """Exposes ``cfg`` to the API routes, which read the environment per call."""
    monkeypatch.setenv("JAGSI_CLOUD_DSN", cfg.dsn)
    monkeypatch.setenv("JAGSI_SOURCE_ID", cfg.source_id)
    monkeypatch.setenv("JAGSI_DEVICE_ID", cfg.device_id)
    monkeypatch.setenv("JAGSI_DB_PATH", str(cfg.db_path))
    monkeypatch.setenv("JAGSI_TREND_MODEL", str(cfg.model_path))
    return cfg
