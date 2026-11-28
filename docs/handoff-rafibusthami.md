# RafiBusthami | Backend, hosted persistence and trend inference

**Deliver to Akmal by Thursday, 26 November.** Give him a running API and a trace he can reproduce from the dashboard. Give Akhnaf the hosted verification results for Saturday’s integration decision. Track delivery in [#28](https://github.com/akhnafyooga/JagSi/issues/28).

## Bring up the candidate

1. Get the candidate SHA, simulated device ID, MQTT prefix, Wokwi launch steps and reviewed model hash from Akhnaf. Confirm the device and prefix match the backend configuration.
2. From `backend/`, configure the team Supabase schema, backend-only DSN, source UUID and model path using the [cloud runbook](cloud-inference.md). Reuse the source UUID when restarting against the same SQLite file. Share a browser-reachable API URL with Akmal.
3. Run `python -m pytest -q` and `python scripts/cloud_check.py --supabase`. Record exit status and database target. This check uses its own source ID. Capture a second trace from the actual Wokwi device for the presentation.
4. In separate terminals run `python -m demo.serve` and `python -m demo.cloud`, then start Wokwi. Inspect `GET /api/health` for broker connectivity and rejected messages, and `GET /api/cloud/status` for mirror progress.

## Prove the backend contract

| Scenario | Procedure and acceptance evidence |
| --- | --- |
| One reading end to end | Change a simulated input. Match its value and receipt time in local telemetry and hosted history. Record device, source, telemetry ID, cloud observation time and measured lag. Target at normal cadence is at most 5 seconds. |
| Trend provenance | Start with a short window and capture `insufficient_data`. After 60 valid readings, request `GET /api/devices/{id}/progress`. Capture state, window bounds, telemetry IDs and model hash. Match the window to `GET /api/devices/{id}/cloud-history?limit=120`. |
| Freshness and dependency loss | Stop telemetry until progress returns `stale`. Resume and observe recovery. Separately verify the unavailable response when the cloud is unreachable. Provide Akmal sanitized HTTP statuses and response bodies so he can distinguish these cases. |
| Backlog and acknowledgment | Record the mirror cursor, stop the worker, keep ingestion running, then trigger and acknowledge an alert. Restart the worker. Confirm the cursor catches up, the alert’s existing row reflects acknowledgment and the replay creates zero duplicate keys for the source. |

## Handoff and presentation

In #28 publish the candidate SHA, device ID, API base URL, startup order, database target, model hash, sanitized response examples, trace IDs, measured lag and per-scenario pass/fail/blocked status. Link logs in [demo evidence](evidence/wokwi-owned-ai/). Akmal accepts the handoff when he can fetch the same history point and interpret the trend response from his presentation machine.

Prepare one slide tracing that reading through MQTT, SQLite, the mirror and hosted inference. If hosted access is blocked, identify the missing dependency and give Akmal a labeled local PostgreSQL run for UI rehearsal. Keep the hosted result pending in [the integration decision](finalization-week.md). Example evidence commit: `docs(cloud): record hosted mirror recovery`.

## Updated handoff for the MCU and daily brief candidate

Use the candidate acceptance checklist in [finalization week](finalization-week.md). The local summary benchmark and scanner fixtures support integration work. Hosted and browser checks still need one shared candidate SHA.

1. **Agree on the API contract with Akmal.** Provide a working API URL, device ID, allowed frontend origin and sanitized examples for fresh, simulated, delayed and absent telemetry. Include `POST /api/devices/{id}/daily-brief`, the local adapter and rules source labels, and the error response for invalid reviewed rows.
2. **Verify the report boundary.** Use fictional reports for the rehearsal. Prove unconfirmed rows stay out of the brief, then replay the same report through review and confirm. Before multi-user release, enforce server-side account, wearer and device association. Add a wrong-wearer regression case and confirm the API rejects it before inference.
3. **Enforce the guidance gate.** An MCU flag can appear as a dated lab fact. Person-specific consumption guidance requires an applicable reviewed plan. Keep the active-alert action independent of the model and hide routine guidance during an unresolved alert. Record behavior with a missing plan, a stopped model worker, stale telemetry and an open SOS.
4. **Verify hosted data and recovery.** Run the Supabase check from #28, trace one Wokwi sample through MQTT, SQLite, the mirror and the API, then restart the mirror and confirm acknowledgment persistence and zero duplicate keys. Record the actual database target and elapsed time.
5. **Hand off to Akmal.** Attach candidate SHA, sanitized request/response pairs, model revision, case IDs, timings and pass/fail/blocked results to [#28](https://github.com/akhnafyooga/JagSi/issues/28). Prepare the backend diagram and trace for the presentation. Use `feat(backend): enforce reviewed guidance eligibility` or `docs(backend): record candidate verification` as appropriate.

## Current rehearsal priority

Use Wokwi as the sensor source. Start Serial Monitor with `scenario stable`, then switch to `scenario rising_hr` for a controlled change. Capture the same device ID, value, timestamp and simulation flag in MQTT, SQLite and the daily-brief API. Collect 60 valid readings for the separate trend check. Pause Wokwi to verify stale handling, then resume and record recovery. Keep MCU results as separately reviewed report input. Give Akmal the tested SHA, API URL, device ID and sample responses before the browser rehearsal. Post hosted persistence and recovery evidence in #28.
