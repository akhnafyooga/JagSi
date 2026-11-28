# JagSi integration PRD and partner handoffs | 25–29 November 2026

**Decision status: proposed.** Akhnaf owns the release decision. Rafi verifies persistence and inference. Akmal coordinates caregiver acceptance. Decide at the Saturday rehearsal using evidence from one candidate SHA, one simulated device and one source database.

Partner instructions: [Rafi’s backend handoff](handoff-rafibusthami.md) and [Akmal’s dashboard handoff](handoff-akmalraflifauzan.md).

## Product outcome and decision criteria

A presenter changes a Wokwi input and a caregiver sees the reading, receives a fall or SOS alert and acknowledges the correct event. The presenter can then show which cloud readings produced a trend. If a dependency fails, the caregiver can tell which functions still work and how old the displayed data are.

Choose the smallest integration that meets the existing R01–R13 requirements. For this week the decisive criteria are alert delivery during cloud interruption, durable acknowledgment, traceability from screen to stored data, and a clean-start rehearsal another teammate can repeat. The demo uses simulated data. Physical-device accuracy is outside this decision. [Team requirements](wokwi-team-requirements.md)

## Integration choices

| Candidate | What the team gains | Cost or failure mode | Proposed disposition |
| --- | --- | --- | --- |
| A. Wokwi → MQTT → FastAPI/SQLite, with a separate worker mirroring to Supabase. Browser uses FastAPI. | Existing bridge and alert flow continue while the cloud is unavailable. Cloud history and model results are auditable. | Two processes to start. Live readings can lead cloud history while the worker catches up. | Preferred for the full demo if the release gates below pass. |
| B. Put Supabase in the synchronous ingestion path and subscribe from the browser. | Browser could consume cloud updates directly. | Requires a new subscription, access-control and reconnect design. A cloud outage would interrupt ingestion unless buffering is rebuilt. | Revisit if remote multi-client delivery becomes a requirement. No candidate evidence currently justifies switching this week. |
| C. Run the current bridge and worker against a local PostgreSQL stand-in. | Exercises mirror, API and dashboard contracts during a venue or cloud outage. Prior backend checks exist. | Cannot establish hosted persistence or venue-to-Supabase connectivity. | Rehearsal and presentation fallback. Label the database target on screen and leave live-cloud acceptance open. |

## Producer and consumer contracts

| Boundary | Implementation handoff | Consumer behavior |
| --- | --- | --- |
| Firmware → bridge | Akhnaf supplies the Wokwi project, device ID, MQTT prefix and a sample payload. Vitals every 2 s. Motion windows contain 30 oldest-first samples at 10 Hz and publish once per second. | Rafi matches topic and payload device IDs and checks rejection counts in `/api/health` after a mismatched fixture. Keep the prefix identical on firmware and bridge. |
| Bridge → mirror | SQLite commits first. Run `python -m demo.serve` and `python -m demo.cloud` separately from backend. Retain the source UUID for the same SQLite file across restarts. | Rafi reconciles cloud rows by `(source_id, kind, record_id)`. Acknowledging an alert must update its existing cloud record. Supply the browser only the API base and device ID. |
| Live vitals and alerts → dashboard | Set `NEXT_PUBLIC_JAGSI_API` and `NEXT_PUBLIC_JAGSI_DEVICE_ID` before the production build. Vitals use `/api/stream` with latest-telemetry polling as fallback. Alerts use `/ws/alerts` with REST acknowledgment at `POST /api/alerts/{alertId}/ack`. | Akmal verifies the same alert ID in two tabs, the REST response and the refreshed log. Make mock, disconnected, stale and live-simulated states visibly distinguishable. |
| Cloud history and trend → dashboard | Use `GET /api/devices/{id}/cloud-history?limit=120` for ordered points and `GET /api/devices/{id}/progress` for the owned trend model. The model consumes 60 cloud readings. | For `ready`, render returned guidance and time range. For `uncertain`, show neutral guidance. For `insufficient_data`, show collection progress. For `stale`, `irregular_sampling` or `missing_values`, explain the state and clear the previous prediction. Handle 503 as unavailable and 404 as a device configuration error. |

**Implementation gap for Akmal.** Monitoring cards currently import mock vitals, history imports fixed series, and the existing AI summary client calls the summary route. On the candidate, identify the exact screens used in the presentation, wire their readings/history/trend to the contracts above and verify each with a varying device input or API state. A successful build alone cannot establish provenance. [Monitoring](../frontend/app/monitoring/page.tsx) · [History](../frontend/app/riwayat/page.tsx) · [API client](../frontend/lib/api.ts) · [Cloud contract](cloud-inference.md)

## Release gates and evidence

| Gate | Test on the same SHA | Passing evidence | Owner |
| --- | --- | --- | --- |
| G1. Live path | Start Wokwi and vary an input. Capture one published reading, dashboard value and matching hosted row. | Same device, corresponding value and timestamps. Normal cloud synchronization target ≤5 s. Record observed wall-clock lag. | Akhnaf + Rafi |
| G2. Emergency flow | Trigger fall and SOS separately. Open two tabs, enable sound by user gesture, acknowledge in one tab, then refresh both. | Correct event type and ID, acknowledged state in both tabs and cloud. For fall, measure final required motion sample at backend receipt to visible alert, target ≤5 s. Separately report event-start-to-screen time. | Akmal + Akhnaf |
| G3. Inference | Start with a short window, collect 60 valid rows, then stop and resume telemetry. Exercise low-confidence and invalid-window cases with controlled fixtures. | API and UI states agree. Record first/last telemetry IDs, model SHA-256, state, confidence when supplied and time range. Label fixture results separately from live observations. | Rafi + Akmal |
| G4. Recovery | Pause mirror, continue ingestion, trigger and acknowledge an alert, then restart mirror against the same SQLite file. | Alert works locally during interruption. Backlog drains and distinct cloud keys match expected records. Updated acknowledgment survives restart. | Rafi |
| G5. Reproducible presentation | A teammate starts the candidate using the handoff and runs the production build with recording enabled. | Record SHA, database target, model hash, commands, run time, observed results and links. Capture build/test output plus a backup clip. | All, Akmal coordinates acceptance |

## Decision at rehearsal

Approve A for the full live presentation when G1–G5 pass against the team project. If hosted access is the only blocker, rerun the workflow with C and identify the hosted check as pending. If the alert, acknowledgment or data provenance check fails, remove the affected live segment and use a previously verified, dated recording only if available. In #30 record the selected candidate, gate results, evidence links, unresolved defects, owners and the presenter responsible for switching to backup. A new candidate SHA requires rerunning the affected gates.

## RafiBusthami — Verify live cloud and inference on the demo candidate

Coordinate with Akhnaf on the candidate SHA and Wokwi device ID. The earlier 20/20 cloud check used local PostgreSQL. For #21 and #10, run `python -m pytest -q` and `python scripts/cloud_check.py --supabase` from backend against the team project. Capture a sanitized cloud row and match its device and timestamp to the live reading. Stop telemetry to check stale inference, then restart the mirror and check backlog recovery and duplicate counts.

Hand Akmal the API base URL, startup steps, device ID and sample fresh and stale responses by Thu 26 Nov. Prepare one architecture slide tracing a reading from MQTT through persistence to inference. Attach the SHA, commands, results and evidence links. Record any missing cloud access as a blocker.

## akmalraflifauzan — Build the dashboard and rehearse caregiver acceptance scenarios

Use Rafi's API base URL and the shared Wokwi device ID. From frontend run `npm ci`, `npm test`, `npm run build` and `npm start`. On the production build, vary an input and match the displayed reading and trend to the API. Trigger a simulated fall, acknowledge it and refresh to verify the acknowledged state persists. Trigger SOS separately and verify its label. Stop and resume telemetry to verify stale and recovered states.

By Fri 27 Nov, hand Akhnaf the SHA, build output, expected and observed results per scenario, screenshots and a short backup recording. Link dashboard results to #22 and notification defects to #13. Present the caregiver workflow at rehearsal.

## akhnafyooga — Integrate the demo candidate and coordinate presentation sign-off

Compare main with the model-training branch, integrate reviewed changes and supply both partners with one candidate SHA, Wokwi launch steps, device ID and reproducible fall and SOS triggers by Wed 25 Nov. Verify firmware startup and model artifacts against the model reproduction guide. Link model and simulation findings to #20.

Lead the Sat 28 Nov rehearsal from a clean start. Route API failures to Rafi, dashboard failures to Akmal and firmware or model failures to Akhnaf. Repeat affected checks after fixes. By Sun 29 Nov collect the final SHA, evidence, deck and backup recording. Introduce the simulation scope, hand off to Rafi for architecture and Akmal for the live workflow, then close with measured results and limitations. Mark each scenario passed, failed or blocked and distinguish synthetic evaluation from live cloud evidence.

## Evidence and commits

Track sign-off in [Rafi’s cloud verification issue](https://github.com/akhnafyooga/JagSi/issues/28), [Akmal’s dashboard acceptance issue](https://github.com/akhnafyooga/JagSi/issues/29) and [Akhnaf’s integration and rehearsal issue](https://github.com/akhnafyooga/JagSi/issues/30).

Store dated, sanitized artifacts in [demo evidence](evidence/wokwi-owned-ai/). Use the [cloud validation guide](cloud-inference.md) and [model reproduction guide](../backend/ml/README.md). A handoff is ready when the recipient can replay the recorded steps on the candidate.

Use `type(scope): short action`. Examples include `docs(demo): add rehearsal evidence`, `feat(api): expose demo trend status`, `fix(ui): clear stale state after reconnect`, `test(dashboard): cover SOS acknowledgment` and `chores(release): organize demo assets`.

## End-to-end acceptance update after the MCU and daily brief benchmarks

The current workspace evidence supports local integration sign-off. The final daily-brief run passed 4,038 checks over 300 cases. One transient rules fallback in the first run remains documented. The scanner matched eight rows and four date lines across four fictional reports. Treat those as extraction fixtures. The blind corpus, noisy reports, wearer association and full browser rehearsal are still open. [Daily brief results](daily-brief-input-quality.md) · [MCU release gates](mcu-scanning-onboarding-prd.md#validation-and-scoring)

| Candidate gate | Owner | Evidence needed |
| --- | --- | --- |
| MCU upload, manual and no-report onboarding | Akmal | Production-build recording and test results from registration through See live. Show that edits appear in the brief only after confirmation. |
| Report belongs to the monitored wearer | Rafi | Server-side ownership and association tests for authorized and wrong-wearer submissions before multi-user release. Use fictional reports in the preview. |
| Grounded and permitted caregiver guidance | Rafi and Akmal | Match displayed facts to reviewed evidence. Verify that the current LDL preview wording is gated before release and that an active alert takes priority even if the worker or cloud is down. |
| Watch freshness and cloud replay | Rafi | Match Wokwi readings to SQLite, Supabase and API timestamps. Record gaps, stale transitions, duplicate counts and restart recovery. |
| Browser alert and recovery | Akmal | Record fall and SOS, audible opt-in, acknowledgment across tabs, stale recovery and measured fall delivery against five seconds. |
| Independent AI and scanner validation | Akhnaf | Publish the blind-set scanner scores and independently labeled model sessions. Report failures and abstentions against each existing threshold. |

Use one candidate SHA for the walkthrough. Include the device ID, model revision, database target and evidence links. Log each gate as passed, failed or blocked. Link partner results to #28 and #29, then record the integrated decision in #30. Existing acceptance thresholds still apply.

### Sensor source for the current rehearsal

Use the existing Wokwi firmware scenarios for watch inputs. Enter `scenario stable` in the Wokwi Serial Monitor to get continuously varying simulated heart rate, SpO₂ and temperature over the normal MQTT path. Use `scenario rising_hr`, `scenario falling_spo2` or `scenario rising_temperature` for deliberate changes. Verify the configured topic prefix and device ID match the API and dashboard. The daily brief takes the latest accepted watch sample. A trend check needs 60 valid readings at about two seconds each. Pause the simulation to exercise stale handling. Enter `scenario off` to return control to the virtual sensors while telemetry continues publishing. The firmware scenarios use their own baseline and jitter. The proposed HTML controls and threshold-band-preserving variation are tracked separately. [Firmware controls](../firmware/jagsi-watch/README.md) · [Stream prerequisites](wokwi-random-stream-prerequisites.md)
