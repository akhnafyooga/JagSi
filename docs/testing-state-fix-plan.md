# JagSi test findings and fix plan

Evidence reviewed on 28 November 2026. Screenshots show an earlier dashboard layout. Record the frontend commit and API URL before repeating the tests on the current branch.

| State | Finding | Evidence |
| --- | --- | --- |
| Normal and high heart-rate readings | Worked in the shown runs | Image 4 shows 78 bpm and a normal banner. Image 1 shows 153 bpm and a warning. Both displayed heart-rate values match the Wokwi serial output. |
| Live health history | Confirmed missing integration | Image 3 shows a fixed weekly graph. The current history route still imports preset series. A chart can render successfully while never showing the selected device’s stored readings. |
| Model-backed AI summary | Live result unverified | Image 2 shows an hour-old summary with no observation window. The current branch calls the progress endpoint. Check whether the screenshot came from an older build and whether the backend returned a fresh model result. |
| MQTT interruption and freshness | Reconnect observed in Wokwi. Dashboard recovery unverified. | Image 3 shows MQTT down followed by reconnection. Capture the dashboard during interruption and after a new reading arrives. |
| Fall, SOS, acknowledgment and chat | Unverified in these screenshots | The chat is empty, and the screenshots do not show an event being triggered or acknowledged. Gapped motion windows are visible in serial output. |

## Fix 1 — connect Riwayat to stored readings

- Replace fixed heart-rate and SpO₂ series with the selected device’s existing telemetry history API. Use the cloud history route if the requirement is specifically to show mirrored records. Confirm available fields and limits before choosing the time range. Use timestamps from returned samples and calculate averages from the displayed points.
- Show loading, empty and unavailable states. Keep missing observations visible as gaps. Remove static weekly health claims and label any demo series separately. Only show steps if a supported source provides them.
- Acceptance test: publish a distinguishable sequence from Wokwi, fetch the same device history and compare chart values, timestamps and averages before and after refreshing. Select a device with no history and verify the empty state.

## Fix 2 — verify the current AI summary against its source window

- Reproduce against the current build using the same device ID, MQTT prefix and backend as Monitoring. Compare latest telemetry, cloud history and the progress response. Save response state, timestamps, sample count and telemetry IDs when present.
- Allow 60 accepted, mirrored readings before judging inference. The current defaults require a 100–180 second window, no gap over six seconds and a newest sample no older than ten seconds. Measure backend receipt timestamps. Wokwi’s displayed simulation clock and wall time may differ.
- If progress is unavailable, check the mirror, cloud configuration and model artifact. If it returns stale or irregular sampling, inspect ingestion cadence and reconnect gaps before adjusting any threshold. If the API is correct and the card differs, trace the browser request and frontend build.
- Acceptance test: show collecting, a valid model-backed summary and stale after stopping the feed. Resume until a fresh valid window forms and verify the card recovers. Use a controlled fixture to check the uncertain state.

## Fix 3 — test freshness and alert recovery

- Disconnect Wokwi while leaving the browser and API running. Check reading age as well as the stream connection. If the app stays live while the last reading ages out, derive stale status from the last accepted reading and keep that reading visibly timestamped. Restore live status when a new reading arrives.
- Record gapped motion windows and accepted/scored counts. Replay a complete labeled fall window, press SOS separately and confirm distinct event sources. Acknowledge in one tab, refresh both tabs and check the same event ID in the log.

## Track the worksheet finding separately

The worksheet reports that its performance retest passed after the icon-font change. It also reports that the dependency scan missed its zero high/critical findings target. Confirm the scan on the current lockfile, review patched versions, update dependencies in a separate change and rerun the build, tests and audit.

For each retest, record the commit, device ID, input, expected result, actual result and timestamped evidence. Start with Riwayat because the missing data integration is confirmed in code.
