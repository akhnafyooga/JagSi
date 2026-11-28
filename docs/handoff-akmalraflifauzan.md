# akmalraflifauzan | Dashboard integration and caregiver demo

**Deliver to Akhnaf by Friday, 27 November.** Supply a reproducible production build, a scenario record and a backup clip. Own the caregiver walkthrough at Saturday’s rehearsal. Track delivery in [#29](https://github.com/akhnafyooga/JagSi/issues/29).

## Build against Rafi’s candidate

Collect the SHA, browser-reachable API URL, device ID, database target and fresh/stale responses from [Rafi’s handoff](handoff-rafibusthami.md). Obtain fall and SOS triggers from Akhnaf. Set `NEXT_PUBLIC_JAGSI_API` and `NEXT_PUBLIC_JAGSI_DEVICE_ID` in `frontend/.env.local` before building. On the presentation machine, run these commands from `frontend/`.

```sh
npm ci
npm test
npm run build
npm start
```

## Connect the screens used in the presentation

| Surface | Work and acceptance contract |
| --- | --- |
| [Monitoring](../frontend/app/monitoring/page.tsx) | Replace fixed readings on the demo cards with the selected device’s live values. Reuse the existing SSE and latest-reading polling path. Show when the input is simulated, stale or disconnected. Verify an input change in both the API and the rendered card. |
| [History](../frontend/app/riwayat/page.tsx) | Bind supported series to ordered points from `GET /api/devices/{id}/cloud-history?limit=120`. Match a chart point to Rafi’s timestamp and value. Omit or explicitly label any series without a live source. |
| Owned trend | Use `GET /api/devices/{id}/progress`. Display the returned window and guidance for `ready`, neutral wording for `uncertain`, and collection progress for `insufficient_data`. Clear obsolete guidance on `stale`, `irregular_sampling`, `missing_values` or HTTP 503. Surface a device configuration error on 404. The existing summary client calls a different endpoint. |
| Emergency alerts | Reuse the app-wide `/ws/alerts` connection and REST acknowledgment fallback. Follow the same alert ID from notification through acknowledgment to the refreshed alert log. |

## Run the caregiver acceptance test

1. Open the production build in two tabs. Confirm the configured device and enable sound with a user gesture. Change a Wokwi input and capture the matching API response, card and history point.
2. Trigger a simulated fall. With Akhnaf, record wall-clock time from backend receipt of the final required motion sample to visible alert, target at most 5 seconds. Record event-start-to-screen time separately. Acknowledge in one tab and verify both tabs after refresh. Trigger SOS separately and check its label and ID.
3. Stop and resume telemetry. Capture the last valid reading, visible stale state and recovery. Use Rafi’s response fixtures to test rare trend states. Label each result as live or fixture-driven.
4. During Rafi’s mirror interruption, confirm local alerts still arrive. After recovery, reconcile the acknowledged alert ID with Rafi’s cloud evidence.

## Handoff and presentation

In #29 record SHA, device, API and database target, build/test results, expected and observed behavior per scenario, timing and artifact links. Put screenshots and the backup clip in [demo evidence](evidence/wokwi-owned-ai/). Send API discrepancies to Rafi with the route, status, timestamp and ID. Send missing firmware events to Akhnaf with the trigger and run time.

Give Akhnaf the replay sequence: vary a reading, show its trend window, trigger a fall, acknowledge it and verify persistence. Identify any failed or blocked segment before the [release decision](finalization-week.md). Example implementation commit: `feat(dashboard): display cloud-backed trend states`.

## Updated handoff for the MCU and daily brief candidate

Use the [candidate acceptance checklist](finalization-week.md) and the API examples from Rafi. Keep the trend endpoint as evidence for the watch model. Verify the daily brief card against the daily-brief endpoint.

1. **Rehearse onboarding in a production build.** From landing and registration, verify upload appears before manual entry. Test a PDF, a photo, manual entry and no report. Edit a candidate row and verify Beranda receives it only after confirmation. Check retry, refresh, smartband guide, the three-second confirm transition and See live.
2. **Trace the daily brief on screen.** Match every displayed value, unit and date to the API. Verify simulated, delayed and missing readings, both model and rules labels, and the alert-first version. Use the same data in two requests to verify that identical responses render identically. Test the reviewed-plan gate with Rafi.
3. **Run Wokwi concurrently.** Change a vital, pause and resume the feed, trigger fall and SOS separately, and acknowledge from one tab. Verify the second tab and refreshed alert log converge on the same alert ID. Capture visible and audible behavior, including alarm opt-in. Measure fall delivery against the five-second target.
4. **Capture evidence at 390, 768 and 1440 px.** Record the build and test output, screenshots for review and Beranda states, and a short backup walkthrough. Check keyboard focus and overflow. Attach the shared SHA, device ID, database target and per-case outcomes to [#29](https://github.com/akhnafyooga/JagSi/issues/29). Use `feat(dashboard): verify reviewed MCU flow` or `docs(dashboard): record caregiver rehearsal` as appropriate.

## Current rehearsal priority

Start from Rafi's tested API URL, candidate SHA and Wokwi device ID. Confirm a fictional MCU report and open Beranda. While Wokwi runs `scenario stable`, verify the readings change and remain labeled as simulated. Switch to `scenario rising_hr` and trace the updated watch value to the API while the confirmed MCU facts retain their own date. Pause and resume Wokwi to verify stale and recovered states. Run fall, SOS and acknowledgment separately. Post production-build output, screenshots, timing and the backup walkthrough in #29.
