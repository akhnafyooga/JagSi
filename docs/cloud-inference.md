# Cloud storage and trend inference (issue #21)

Owner: Rafi · Requirements R07, R08, R09 and R12 in [the Wokwi team requirements](wokwi-team-requirements.md).

This is the implementation of sections 10 and 11 of that plan, with the changes listed at the end. Akhnaf's firmware and models (#20) and Akmal's dashboard (#22) connect to the contracts below.

```text
Wokwi / replay -> MQTT -> FastAPI bridge -> SQLite (unchanged, durable staging)
                                            |
                      python -m demo.cloud  |  reads committed rows, 200 per transaction
                                            v
                                Supabase public.jagsi_demo_records
                                            |
            GET /api/devices/{id}/progress  |  last 60 readings -> checks -> trend model
                                            v
                          result + reviewed guidance, stored back as kind='analysis'
```

## API contract for the dashboard (#22)

| Route | Returns |
| --- | --- |
| `GET /api/devices/jagsi-watch-01/progress` | 200 with `state` = `ready`, `uncertain`, `insufficient_data`, `stale`, `irregular_sampling` or `missing_values`. 503 when the cloud or the trend model is unavailable, 404 for another device. |
| `GET /api/devices/jagsi-watch-01/cloud-history?limit=120` | 200 `{points: [...]}` oldest first. Each point has `received_at`, `heart_rate`, `spo2`, `body_temperature`, `telemetry_id`, `simulated`. 503 if the cloud is down. |
| `GET /api/cloud/status` | Row counts per kind, the mirror cursor, the newest cloud reading. |

A `ready` or `uncertain` result also carries `label`, `confidence`, `probabilities`, `guidance`, `model_version`, `model_sha256`, `from`, `to`, `telemetry_ids` (first and last stored row used), `sample_count`, `span_seconds` and `stats.first_10_mean` / `stats.last_10_mean`. Only `ready` shows the label's guidance; `uncertain` (confidence below 0.65) shows a neutral message. Every other state carries no label, so the UI cannot show a prediction for bad input.

## Contract for the trend model (#20)

`demo/train_trends.py` is the feature contract copied from section 9 of the plan. The API loads `JAGSI_TREND_MODEL` (default `demo/artifacts/trend_model.joblib`) and refuses, with 503, an artifact whose `features` list differs from `FEATURES` or whose `rows` is not 60. Retraining, the metrics, the model card and the published hash stay with #20. The artifact is not committed by this change.

## Set up Supabase (once)

1. Sign in at https://supabase.com and create a Free project in the team organization. Keep the database password in the team's secret store.
2. Open **SQL Editor**, paste all of [`backend/demo/schema.sql`](../backend/demo/schema.sql) and run it. It is safe to run again.
3. Open **Connect**, choose **Session pooler**, copy the URI. Replace `[YOUR-PASSWORD]` with the URL-encoded password and add `?sslmode=require`.
4. Copy `backend/.env.demo.example` to `backend/.env.demo` and fill in `JAGSI_CLOUD_DSN`, `JAGSI_TOPIC_BASE` (the team's shared prefix) and a new `JAGSI_SOURCE_ID`:
   - macOS: `uuidgen | tr A-Z a-z`
   - PowerShell: `[guid]::NewGuid().ToString()`
5. Check `git status`: `.env.demo` must not appear. It is in `.gitignore`.

## Run the demo (from `backend/`)

```bash
pip install -r requirements-dev.txt -r requirements-demo.txt
python -m demo.train_trends          # until #20 delivers the reviewed artifact
python -m demo.serve                 # terminal A: API on 127.0.0.1:8000 with .env.demo loaded
python -m demo.cloud                 # terminal B: mirror worker
```

Then start Wokwi. After about two minutes of readings, open `http://127.0.0.1:8000/api/devices/jagsi-watch-01/progress`.

Before the demo, run the same checks against Supabase. It writes under a fresh random source ID, so it never mixes with the real demo rows:

```bash
python scripts/cloud_check.py --supabase
```

## Failure behaviour

| Situation | What happens |
| --- | --- |
| Cloud unreachable or paused | The bridge keeps storing in SQLite. The worker logs the failure and retries after 5, 10, 20... up to 60 s. On reconnection it catches up 200 rows per transaction. |
| Batch fails half way | The whole transaction rolls back, including the cursor. The next attempt starts from the same row. |
| Worker restarted, or rows sent twice | Upsert on `(source_id, kind, record_id)`. Unchanged rows are not rewritten. |
| Alert acknowledged after it was mirrored | Alert snapshots are compared every pass and the changed one is updated. |
| Two workers for one source ID | A PostgreSQL advisory lock lets only one run. The other waits. |
| Same source ID on another laptop, or SQLite deleted but UUID kept | The cursor stores a fingerprint of the SQLite file. The worker stops with exit code 2 instead of mixing two row-ID sequences. Generate a new UUID. |
| Cloud not configured | The API still starts. The three cloud routes answer 503 with the reason. |

The bridge also now rejects, and counts in `/api/health` under `messages_rejected`: a payload whose `device_id` differs from its topic, any device other than `JAGSI_DEVICE_ID` when `JAGSI_RESTRICT_DEVICE=true`, payloads over 16 KB, and motion windows holding NaN, Infinity or booleans. A refused broker connection shows in `last_connect_error`.

## Changes from the reference code in the plan

- Configuration is read per call, not at import. The reference raised `KeyError` at import without `.env.demo`, which would have stopped the API and every existing test.
- The cursor stores a SQLite fingerprint, and an advisory lock prevents two workers from running together. The plan asked for a source-ID collision test, but the reference code could not detect a collision.
- Unchanged alert snapshots are not rewritten on every pass.
- Readings with NaN or Infinity count as `missing_values`, so they never reach the model.
- The result adds `telemetry_ids`, `model_sha256` and per-class `probabilities` for traceability (R09).
- `demo/serve.py` replaces the one-line PowerShell wrapper and works on macOS too.
- `simulated` comes from the stored row's flag, not a constant.

## Validation record

22 November 2026, branch `feat/week9-cloud-inference`, Python 3.13, PostgreSQL 16.15 (local stand-in for Supabase).

| Check | Result |
| --- | --- |
| `python -m pytest -q` | 165 passed. 124 tests existed before. New: 27 cloud tests, 4 secrets tests, 10 input-validation tests. |
| Mutation check | Disabling the collision check, the missing-value check or the unchanged-row filter each makes a test fail. |
| `scripts/cloud_check.py` | 20/20 at the 2 s firmware cadence. 5 readings mirrored within 5 s. A 10-row backlog caught up after the worker was stopped. SOS acknowledgment reached the cloud. Rising heart rate classified `rising_hr`, confidence 0.987, over telemetry IDs 1–60 spanning 120 s, answered in 36 ms. No duplicates after a restart. `stale` 11 s after the feed stopped. |
| Existing checks | `integration_check.py` 22/22, `eventgrid_check.py` 17/17, `alert_ws_check.py` 13/13. |
| Reference trend model | Macro-F1 1.0 on 150 held-out synthetic sessions (the same generator). This is a smoke test, not an evaluation; see #20. |

Not yet done, and needed before closing #21: running `cloud_check.py --supabase` against the team project, and the live Wokwi run with screenshots of the Supabase table. Both need the team's Supabase project. Output: [`docs/evidence/wokwi-owned-ai/`](evidence/wokwi-owned-ai/).
