# Week 8 validation results

What was built for issues #13 and #14, two fixes found while doing it, what was run
to check it, and what is still open. Every number below comes from a command that
can be re-run.

## Summary

| Issue | Built this week | Verified by | Still needs |
|-------|-----------------|-------------|-------------|
| #13 Real-time notifications | `WS /ws/alerts`, thread-safe event hub, full-screen emergency alert, alarm tone, system notification, live fall card, live alert log, bell counter | 20 backend tests, 27 new frontend tests, 13-check end-to-end run, screenshots | a test on the caregiver's real phone (sound and notifications depend on the browser) |
| #14 README & docs | README structure, setup, real-time and CI sections rewritten to match the repo; Gantt chart completed; Mermaid diagrams drawn on GitHub Pages; status table per issue | reading the rendered pages | the team to confirm the Sprint 2 and 3 dates in the Gantt chart |
| #10 (Week 7 leftover) | default Gemini model fixed to `gemini-3.8-flash` | 1 new test that compares code and README | a `GEMINI_API_KEY` |
| #12 (found on the way) | icon sizes were ignored on every page | 2 new tests, screenshots | none |

## 1. Test suites

```
cd backend && python3 -m pytest -q
124 passed                      (was 103 in Week 7)

cd backend && python3 scripts/alert_ws_check.py
13 checks, 13 passed, 0 failed  (new: watch -> MQTT -> backend -> /ws/alerts -> ack -> watch)

cd backend && python3 scripts/integration_check.py
22 checks, 22 passed, 0 failed  (unchanged)

cd backend && python3 scripts/eventgrid_check.py
17 checks, 17 passed, 0 failed  (unchanged)

cd frontend && npx vitest run && npx tsc --noEmit && npm run lint && npm run build
58 passed (was 31), types clean, no lint errors, production build succeeds
```

The alert check now runs in CI as "Real-time alert check (WebSocket)".

## 2. Real-time emergency notifications (#13)

Until this week an alert only appeared if the caregiver happened to open the
Darurat page, and that page showed the demo list from issue #12. The fall card on
Beranda always said "Aman", and the bell's red dot was always on.

### How it works now

```
watch --MQTT/IoT Hub--> bridge --> SQLite --> Hub --> WS /ws/alerts --> every open dashboard
                                                          |
watch <--ack_alert-- bridge <--- "Saya tangani" ----------+
```

- The backend pushes `alert` the moment it stores one. On connect it sends `hello`
  with every alert nobody has handled, so a phone that wakes up still sees an alert
  that fired while it was asleep.
- The dashboard shows a full-screen red alert on whatever page is open, with the
  vitals the watch sent, an alarm tone (Web Audio, no file to download), vibration
  on phones, and a system notification when the tab is in the background.
- Only **Saya tangani** closes the screen; **Matikan suara** stops the sound only.
  The acknowledgement goes back on the same socket, is stored, is sent to the watch
  as `ack_alert` (so it stops re-sending), and closes the alert on every other open
  dashboard.
- If the socket is down, the button uses `POST /api/alerts/{id}/ack` instead. The
  dashboard reconnects after 1 s, 2 s, 4 s ... up to 30 s.
- Telemetry stays on server-sent events. Only alerts needed a reply channel.

### Measured

| What | Result |
|------|--------|
| SOS from the fake watch to the WebSocket, 5 presses (`alert_ws_check.py`) | median 6 ms, max 47 ms |
| Fall published to the broker until the emergency screen is visible in Chromium | 56 ms |
| "Saya tangani" on one dashboard until the screen closes on a second one | 95 ms |
| Acknowledgement through the REST API until the socket hears it | 3 ms |

FR 2 asks for emergency alerts within 5 seconds. The backend-to-dashboard part
now takes well under a tenth of a second on a local network; the watch-to-cloud
part depends on Wi-Fi and, in Azure mode, IoT Hub.

### Security decision

Browsers do not apply CORS to WebSockets. Without a check, any website the
caregiver opened could connect to `/ws/alerts` and acknowledge (silence) a fall
alert. The socket compares the `Origin` header with `JAGSI_CORS_ORIGINS` and
refuses anything else with HTTP 403 (tested both in pytest and end to end).
Messages are limited to 1 KB and an alert id to 100 characters.

### Thread safety

Events are published from the MQTT network thread, FastAPI's threadpool and the
event loop. The Week 6 SSE code put events into `asyncio.Queue` directly from the
threadpool, which is not thread-safe. Measured on the real server it still
delivered in about 10 ms, because the threadpool wakes the loop when the request
finishes, so it was a latent problem rather than a visible delay. `app/realtime.py`
now hands every event over with `loop.call_soon_threadsafe`, and a test publishes
from a bare thread and requires delivery within 0.5 s.

### Screenshots

Taken from the running stack (local broker, backend, `next start`, fake watch)
with a 430 px wide phone viewport:

- `evidence/week8-home-before.png`: Beranda asking to turn the alarm on once
- `evidence/week8-home-armed.png`: live vitals, fall card "Aman"
- `evidence/week8-emergency-fall.png`: fall alert with the vitals from the watch
- `evidence/week8-emergency-sos.png`: SOS alert, on a second dashboard tab
- `evidence/week8-home-after.png`: back to "Aman" after Saya tangani
- `evidence/week8-darurat-log.png`: alert history from the backend, all handled

**Not verified here:** sound and system notifications on a real phone. The headless
test browser has no speaker and reports notifications as blocked.

## 3. README and documentation (#14)

- README: "Project Structure" described a suggested layout (`hardware/`,
  `backend/ai/`) that never existed; "Getting Started" said the commands were not
  known yet; "CI/CD" described Node.js 18 and only `main`. All three now describe
  the repository as it is, with a new "Real-time Notifications" section and a
  status column for the six-sprint roadmap.
- `docs/index.md`: the Gantt chart stopped after its first Sprint 2 line with an
  incomplete end date (`2026-10`), and was not marked as Mermaid, so the site showed
  it as text. It now lists Sprints 1 to 3 with their status, followed by a table
  of every issue. Sprint 2 and 3 dates continue Sprint 1's two-week cadence and
  should be confirmed by the team.
- `docs/_includes/head-custom.html`: GitHub Pages does not draw Mermaid blocks
  (github.com does, which is why nobody noticed). This loads Mermaid on the site so
  the ERD and the Gantt chart are drawn.
- `backend/README.md`: the alert WebSocket, its messages, the origin rule and the
  new check script.

## 4. Fixes found on the way

**Gemini model (Week 7 leftover, #10).** `docs/week7-validation.md`, the backend
README and the Week 7 report all say the default model is `gemini-3.8-flash`, but
`config.py` still defaulted to `gemini-2.5-flash`. Google's model list now says
2.5 Flash is available only to projects that used it before, so a new key would
have failed and every summary would have fallen back to the rules without anyone
noticing. The default is now `gemini-3.8-flash`, and a test fails if the code and
the README disagree again.

**Icon sizes (#12).** Google's icon stylesheet loads after the app's CSS and sets
`font-size: 24px`, so every icon was 24 px whatever size the code asked for (the
40 px SOS button on Darurat included). The Week 7 screenshots could not load the
font, so it did not show there. `Icon` now applies the size inline.

## 5. Still open

- #8: run `infra/azure/deploy.sh` on the team's Azure subscription.
- #9: record the physical MPU6050 (`docs/recording-protocol.md`) and re-tune the
  threshold; the stored 0.11 still flags walking as a fall.
- #12: Monitoring and Riwayat still show demo data.
- #7: casing and wearable prototype.
- The Week 6 to Week 8 work is still on local branches; PR #18 is still open.
