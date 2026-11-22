"""Cloud mirror (R07, R08), trend inference (R09) and failure handling (issue #21).

Each test names the defect it protects against (section 14 of
docs/wokwi-team-requirements.md).
"""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone

import psycopg
import pytest
from fastapi.testclient import TestClient

from demo import cloud as cloudmod
from demo.cloud import (
    BATCH_SIZE,
    LocalDatabaseMissing,
    MirrorBusy,
    SourceCollision,
    connect,
    mirror_once,
    predict,
)

from .conftest import DEVICE, LocalDB


def rows_of(conn, source, kind):
    return conn.execute(
        "select record_id, payload from public.jagsi_demo_records "
        "where source_id=%s and kind=%s order by record_id::text",
        (source, kind),
    ).fetchall()


def count(conn, source, kind):
    return conn.execute(
        "select count(*) from public.jagsi_demo_records where source_id=%s and kind=%s",
        (source, kind),
    ).fetchone()[0]


def cursor_of(conn, source):
    row = conn.execute(
        "select payload from public.jagsi_demo_records "
        "where source_id=%s and kind='cursor' and record_id='telemetry'",
        (source,),
    ).fetchone()
    return row[0] if row else None


def stable(n=60):
    return [(75 + (i % 3) - 1, 98.0, 36.6) for i in range(n)]


# -- schema ------------------------------------------------------------------------
def test_schema_can_be_run_twice(pg_dsn):
    with psycopg.connect(pg_dsn, autocommit=True) as conn:
        conn.execute(cloudmod.BACKEND_DIR.joinpath("demo", "schema.sql").read_text())
        rls = conn.execute(
            "select relrowsecurity from pg_class where relname='jagsi_demo_records'"
        ).fetchone()[0]
        grants = conn.execute(
            "select count(*) from information_schema.role_table_grants "
            "where table_name='jagsi_demo_records' and grantee in ('anon','authenticated')"
        ).fetchone()[0]
    assert rls is True
    assert grants == 0


# -- mirror: R07 -------------------------------------------------------------------
def test_mirror_copies_rows_and_advances_cursor(cfg, cloud, local_db):
    ids = local_db.add_series(stable(5))
    result = mirror_once(cfg)
    assert result.telemetry == 5
    assert result.last_id == ids[-1]
    stored = rows_of(cloud, cfg.source_id, "telemetry")
    assert sorted(int(r[0]) for r in stored) == ids
    assert stored[0][1]["heart_rate"] in (74, 75, 76)
    assert stored[0][1]["simulated"] is True
    assert cursor_of(cloud, cfg.source_id)["last_id"] == ids[-1]


def test_replay_adds_no_duplicates(cfg, cloud, local_db):
    """Defect: re-sending rows after a restart doubled the history."""
    local_db.add_series(stable(10))
    mirror_once(cfg)
    # Simulate a worker that lost its place: rewind the cursor to zero.
    cloud.execute(
        "update public.jagsi_demo_records set payload = jsonb_set(payload, '{last_id}', '0') "
        "where source_id=%s and kind='cursor'", (cfg.source_id,))
    again = mirror_once(cfg)
    assert again.telemetry == 10  # it re-read them...
    assert count(cloud, cfg.source_id, "telemetry") == 10  # ...and stored no copies
    assert mirror_once(cfg).telemetry == 0


def test_restart_keeps_history_and_source(cfg, cloud, local_db):
    """Restart and cloud history: a new worker continues from the saved cursor."""
    local_db.add_series(stable(3))
    mirror_once(cfg)
    restarted = dataclasses.replace(cfg)  # same env, new process
    local_db.add_telemetry(datetime.now(timezone.utc))
    assert mirror_once(restarted).telemetry == 1
    assert count(cloud, cfg.source_id, "telemetry") == 4


# -- mirror: R08 -------------------------------------------------------------------
def test_backlog_catches_up_in_batches_after_outage(cfg, cloud, local_db):
    start = datetime.now(timezone.utc) - timedelta(hours=1)
    for i in range(2 * BATCH_SIZE + 50):
        local_db.add_telemetry(start + timedelta(seconds=2 * i))

    def offline(_cfg):
        raise psycopg.OperationalError("network unreachable")

    for _ in range(3):
        with pytest.raises(psycopg.OperationalError):
            mirror_once(cfg, connector=offline)
    assert count(cloud, cfg.source_id, "telemetry") == 0

    batches = []
    while True:
        result = mirror_once(cfg)
        batches.append(result.telemetry)
        if result.caught_up:
            break
    assert batches == [BATCH_SIZE, BATCH_SIZE, 50]
    assert count(cloud, cfg.source_id, "telemetry") == 2 * BATCH_SIZE + 50


def test_failed_batch_rolls_back_cursor_and_rows(cfg, cloud, local_db):
    """Defect: a batch that failed half way advanced the cursor past lost rows."""
    local_db.add_series(stable(20))

    class Flaky:
        """Wraps a real connection; the 12th telemetry insert fails."""

        def __init__(self, real):
            self.real, self.inserts = real, 0

        def execute(self, sql, params=None):
            if "insert into public.jagsi_demo_records" in sql and params[1] == "telemetry":
                self.inserts += 1
                if self.inserts == 12:
                    raise psycopg.OperationalError("connection reset mid-batch")
            return self.real.execute(sql, params)

        def __enter__(self):
            self.real.__enter__()
            return self

        def __exit__(self, *exc):
            return self.real.__exit__(*exc)

    with pytest.raises(psycopg.OperationalError):
        mirror_once(cfg, connector=lambda c: Flaky(connect(c)))
    assert count(cloud, cfg.source_id, "telemetry") == 0
    assert cursor_of(cloud, cfg.source_id) is None

    assert mirror_once(cfg).telemetry == 20
    assert cursor_of(cloud, cfg.source_id)["last_id"] == 20


def test_alert_status_change_reaches_cloud(cfg, cloud, local_db):
    local_db.add_alert("sos-1")
    assert mirror_once(cfg).alerts_changed == 1
    local_db.set_alert_status("sos-1", "acknowledged")
    assert mirror_once(cfg).alerts_changed == 1
    (record_id, payload), = rows_of(cloud, cfg.source_id, "alert")
    assert record_id == "sos-1"
    assert payload["status"] == "acknowledged"
    assert payload["vitals"] == {"heart_rate": 80}
    assert mirror_once(cfg).alerts_changed == 0  # unchanged snapshots cost no writes


def test_source_id_collision_is_refused(cfg, cloud, local_db, tmp_path):
    """Defect: two laptops with one UUID overwrote each other's telemetry IDs."""
    local_db.add_series(stable(5))
    mirror_once(cfg)

    other = LocalDB(tmp_path / "other-laptop.db")
    other.add_telemetry(datetime.now(timezone.utc) - timedelta(days=1), hr=90)
    other.add_series(stable(8))
    with pytest.raises(SourceCollision):
        mirror_once(dataclasses.replace(cfg, db_path=other.path))
    assert count(cloud, cfg.source_id, "telemetry") == 5  # nothing was overwritten


def test_replaced_sqlite_file_is_refused(cfg, cloud, local_db, tmp_path):
    local_db.add_series(stable(5))
    mirror_once(cfg)
    fresh = LocalDB(tmp_path / "fresh.db")  # deleted and recreated, kept the UUID
    with pytest.raises(SourceCollision):
        mirror_once(dataclasses.replace(cfg, db_path=fresh.path))


def test_two_sources_stay_separate(cfg, cloud, local_db, tmp_path):
    local_db.add_series(stable(4))
    other = LocalDB(tmp_path / "b.db")
    other.add_series(stable(6))
    other_cfg = dataclasses.replace(cfg, source_id="00000000-0000-4000-8000-000000000002",
                                    db_path=other.path)
    mirror_once(cfg)
    mirror_once(other_cfg)
    assert count(cloud, cfg.source_id, "telemetry") == 4
    assert count(cloud, other_cfg.source_id, "telemetry") == 6


def test_second_worker_for_same_source_waits(cfg, cloud, local_db):
    local_db.add_series(stable(2))
    with psycopg.connect(cfg.dsn) as holder:
        holder.execute("select pg_advisory_xact_lock(%s)",
                       (cloudmod._advisory_key(cfg.source_id),))
        with pytest.raises(MirrorBusy):
            mirror_once(cfg)
    assert mirror_once(cfg).telemetry == 2


def test_missing_sqlite_is_reported(cfg, tmp_path):
    with pytest.raises(LocalDatabaseMissing):
        mirror_once(dataclasses.replace(cfg, db_path=tmp_path / "nope.db"))


def test_worker_exits_on_collision(cfg, cloud, local_db, tmp_path, monkeypatch, cloud_env):
    local_db.add_series(stable(2))
    assert cloudmod.run_worker(once=True) == 0
    other = LocalDB(tmp_path / "c.db")
    other.add_telemetry(datetime.now(timezone.utc) - timedelta(days=2))
    monkeypatch.setenv("JAGSI_DB_PATH", str(other.path))
    assert cloudmod.run_worker(once=True) == 2


# -- inference: R09 and the "no prediction on bad input" checks ---------------------
def mirrored(cfg, local_db, values, end=None, step_s=2.0):
    local_db.add_series(values, end=end, step_s=step_s)
    while not mirror_once(cfg).caught_up:
        pass
    with connect(cfg) as conn:
        return cloudmod._latest_telemetry(conn, cfg, 60)


def test_insufficient_data(cfg, cloud, local_db):
    result = predict(mirrored(cfg, local_db, stable(30)), cfg)
    assert result["state"] == "insufficient_data"
    assert result["count"] == 30


def test_stale_window_gives_no_prediction(cfg, cloud, local_db):
    old = datetime.now(timezone.utc) - timedelta(minutes=5)
    result = predict(mirrored(cfg, local_db, stable(), end=old), cfg)
    assert result["state"] == "stale"
    assert "label" not in result


def test_irregular_sampling_gives_no_prediction(cfg, cloud, local_db):
    now = datetime.now(timezone.utc)
    local_db.add_series(stable(30), end=now - timedelta(seconds=80))  # 20 s hole after this
    rows = mirrored(cfg, local_db, stable(30), end=now)
    result = predict(rows, cfg)
    assert result["state"] == "irregular_sampling"
    assert result["max_gap_seconds"] > 6


def test_missing_values_give_no_prediction(cfg, cloud, local_db):
    values = stable()
    values[40] = (None, 98.0, 36.6)
    result = predict(mirrored(cfg, local_db, values), cfg)
    assert result["state"] == "missing_values"
    assert result["rows_with_missing_values"] == 1


def test_stable_window_is_traceable(cfg, cloud, local_db):
    rows = mirrored(cfg, local_db, stable())
    result = predict(rows, cfg)
    assert result["state"] == "ready"
    assert result["label"] == "stable"
    assert result["guidance"] == cloudmod.GUIDANCE["stable"]
    assert result["model_version"] == "synthetic-trends-v1"
    assert len(result["model_sha256"]) == 64
    # R09: the answer names the stored rows and times it was computed from.
    assert result["telemetry_ids"] == [rows[0]["telemetry_id"], rows[-1]["telemetry_id"]]
    assert result["from"].startswith(rows[0]["received_at"][:19])
    assert result["to"].startswith(rows[-1]["received_at"][:19])
    assert result["sample_count"] == 60
    assert result["simulated"] is True


def test_rising_heart_rate_is_recognised(cfg, cloud, local_db):
    values = [(72 + 28 * i / 59, 98.0, 36.6) for i in range(60)]
    result = predict(mirrored(cfg, local_db, values), cfg)
    assert result["label"] == "rising_hr"
    assert result["state"] == "ready"
    assert result["stats"]["last_10_mean"]["heart_rate"] > result["stats"]["first_10_mean"]["heart_rate"]


# -- API routes -------------------------------------------------------------------
@pytest.fixture
def api():
    from app.main import app

    return TestClient(app)


def test_progress_endpoint_stores_analysis(api, cloud_env, cloud, local_db):
    cfg = cloud_env
    mirrored(cfg, local_db, stable())
    body = api.get(f"/api/devices/{DEVICE}/progress").json()
    assert body["state"] == "ready"
    analyses = rows_of(cloud, cfg.source_id, "analysis")
    assert len(analyses) == 1
    record_id, payload = analyses[0]
    assert record_id == f"{body['telemetry_ids'][1]}-synthetic-trends-v1"
    assert payload["label"] == body["label"]
    # Asking again for the same window stores no second analysis.
    api.get(f"/api/devices/{DEVICE}/progress")
    assert count(cloud, cfg.source_id, "analysis") == 1


def test_progress_reports_insufficient_data_as_200(api, cloud_env, cloud, local_db):
    mirrored(cloud_env, local_db, stable(10))
    response = api.get(f"/api/devices/{DEVICE}/progress")
    assert response.status_code == 200
    assert response.json()["state"] == "insufficient_data"
    assert count(cloud, cloud_env.source_id, "analysis") == 0


def test_missing_model_is_503(api, cloud_env, cloud, local_db, monkeypatch, tmp_path):
    mirrored(cloud_env, local_db, stable())
    monkeypatch.setenv("JAGSI_TREND_MODEL", str(tmp_path / "absent.joblib"))
    response = api.get(f"/api/devices/{DEVICE}/progress")
    assert response.status_code == 503
    assert "Trend model unavailable" in response.json()["detail"]


def test_wrong_feature_contract_is_503(api, cloud_env, cloud, local_db, monkeypatch, tmp_path):
    import joblib

    artifact = joblib.load(cloud_env.model_path)
    artifact["features"] = list(reversed(artifact["features"]))
    bad = tmp_path / "bad.joblib"
    joblib.dump(artifact, bad)
    mirrored(cloud_env, local_db, stable())
    monkeypatch.setenv("JAGSI_TREND_MODEL", str(bad))
    assert api.get(f"/api/devices/{DEVICE}/progress").status_code == 503


def test_unreachable_cloud_is_503(api, cloud_env, monkeypatch):
    monkeypatch.setenv("JAGSI_CLOUD_DSN", "postgresql://nobody@127.0.0.1:1/none?connect_timeout=1")
    for path in (f"/api/devices/{DEVICE}/progress", f"/api/devices/{DEVICE}/cloud-history",
                 "/api/cloud/status"):
        assert api.get(path).status_code == 503, path


def test_cloud_not_configured_is_503(api, monkeypatch):
    monkeypatch.delenv("JAGSI_CLOUD_DSN", raising=False)
    monkeypatch.delenv("JAGSI_SOURCE_ID", raising=False)
    response = api.get(f"/api/devices/{DEVICE}/progress")
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_unknown_device_is_404(api, cloud_env):
    assert api.get("/api/devices/someone-else/progress").status_code == 404
    assert api.get("/api/devices/someone-else/cloud-history").status_code == 404


def test_cloud_history_and_status(api, cloud_env, cloud, local_db):
    ids = local_db.add_series(stable(5))
    mirror_once(cloud_env)
    history = api.get(f"/api/devices/{DEVICE}/cloud-history").json()
    assert [p["telemetry_id"] for p in history["points"]] == ids  # oldest first
    status = api.get("/api/cloud/status").json()
    assert status["counts"]["telemetry"] == 5
    assert status["cursor"]["last_id"] == ids[-1]
