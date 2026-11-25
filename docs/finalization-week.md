# JagSi finalization week | 25–29 November 2026

Proposed schedule in Jakarta time. All three owners should use the same candidate SHA and simulated device ID. Record the run time so telemetry, cloud rows and dashboard screenshots can be compared.

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
