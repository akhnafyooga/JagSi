-- JagSi cloud storage for the Wokwi demo (issue #21, requirement R07).
--
-- Run once in the Supabase SQL Editor. Safe to run again: every statement is
-- idempotent.
--
-- One table holds four kinds of record, all keyed by the local database they
-- came from (source_id), so two laptops mirroring into the same project never
-- overwrite each other's rows:
--   telemetry  one row of telemetry_data from the backend's SQLite
--   alert      the latest snapshot of one alert_event row (status changes too)
--   cursor     how far the mirror has got, plus a fingerprint of the SQLite file
--   analysis   one trend-model result, traceable to its telemetry rows
--
-- The browser never talks to this table. The FastAPI backend connects with the
-- server-side database URI, so row level security is switched on and the
-- browser roles get no grants at all.

create table if not exists public.jagsi_demo_records (
  source_id   uuid        not null,
  kind        text        not null check (kind in ('telemetry', 'alert', 'cursor', 'analysis')),
  record_id   text        not null,
  device_id   text        not null,
  observed_at timestamptz not null,
  payload     jsonb       not null,
  primary key (source_id, kind, record_id)
);

create index if not exists jagsi_demo_device_time
  on public.jagsi_demo_records (source_id, device_id, kind, observed_at desc);

alter table public.jagsi_demo_records enable row level security;
revoke all on public.jagsi_demo_records from anon, authenticated;
