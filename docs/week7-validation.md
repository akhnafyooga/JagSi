# Week 7 validation results

What was built for issues #8, #9 and #10, what was run to check it, and what is
still left for the team because it needs an Azure account, the physical watch or
a Gemini key. Every number below comes from a command that can be re-run.

## Summary

| Issue | Built this week | Verified by | Still needs |
|-------|-----------------|-------------|-------------|
| #8 Azure IoT Hub & Event Grid | firmware TLS + X.509 transport, Event Grid webhook, direct-method commands, deploy script | 23 unit tests, 17-check Event Grid replay, sketch type-check in both transports, 11 firmware checks | running `infra/azure/deploy.sh` on the team's Azure subscription and a Wokwi run against the real hub |
| #9 fall threshold | labelled recording API, re-tune script that scores falls per session | 10 recorder tests, 7 re-tune tests incl. an end-to-end run with the real model | recordings from the physical MPU6050 (`docs/recording-protocol.md`) |
| #10 Gemini health summary | summary + chat endpoints, rule-based fallback, dashboard card and chat wired to them | 18 backend tests, 9 new frontend tests, screenshots | a `GEMINI_API_KEY` for live Gemini answers |

## 1. Test suites

```
cd backend && python3 -m pytest -q
103 passed                      (was 45 in Week 6)

cd backend && python3 scripts/integration_check.py
22 checks, 22 passed, 0 failed  (Week 6 MQTT pipeline, unchanged behaviour)

cd backend && python3 scripts/eventgrid_check.py
17 checks, 17 passed, 0 failed  (new: the same pipeline over Azure)

cd frontend && npx vitest run && npx tsc --noEmit && npm run build
31 passed (was 22), types clean, production build succeeds

firmware/test/check_sketch.sh /tmp/ArduinoJson/src
sketch.ino type-checks in both transports

g++ ... firmware/test/test_azure_method.cpp && ./a.out
11 checks, 0 failures
```

All of these now run in CI (`.github/workflows/main.yml`).

## 2. Azure IoT Hub (#8)

`scripts/eventgrid_check.py` replays what Azure would deliver, built from the
documented Event Grid schema, through the real webhook, bridge, classifier and
database. It checks the validation handshake, a wrong webhook key (401),
connect/disconnect events, telemetry, 20 walking windows, a fall window, a
malformed window, an SOS sent twice (stored once, acked twice by direct method),
a payload claiming another device's id (refused), and a dashboard command going
out as a direct method.

Security decisions worth knowing:

- The device id comes from IoT Hub's authenticated connection, not from the
  payload. A watch claiming to be another watch is refused with HTTP 400.
- The webhook requires a shared key; the backend refuses to start in azure mode
  without one.
- The backend uses the `service` policy, which can call direct methods but cannot
  create or delete devices.
- The device private key is generated locally and never committed
  (`.gitignore`); the firmware checks Azure's server certificate against the
  DigiCert Global Root G2 and Microsoft RSA Root 2017 certificates.

**Not verified here:** a real connection from Wokwi to a real IoT hub. The ESP32
toolchain could not be downloaded in the build environment, so the firmware was
type-checked against stand-in Arduino headers instead of compiled for the board.
The first real run is step 5 of `docs/azure-setup.md`.

### Finding: the free tier runs out in about 1.5 hours

IoT Hub F1 allows 8,000 messages a day. The watch sends about 1.5 messages a
second (a motion window every second, telemetry every 2 s), so the daily quota
is gone after roughly 90 minutes. For demos, run the watch only while presenting
or stop the motion stream with `set_motion`; for longer runs use S1.

## 3. Fall threshold tooling (#9)

The re-tune script scores a fall recording per session (detected if any window
reaches the threshold), and non-fall recordings by the alerts the backend would
actually raise, using its 15 s cooldown. Run on synthetic recordings to prove the
pipeline (real recordings will replace these):

```
threshold      fall_recall  alert_precision  false_alerts_per_hour
0.11 (stored)  1.0          0.2              240.0
0.56 (chosen)  1.0          1.0              0.0
Choice: meets both targets for thresholds 0.18 to 0.95; middle of that range chosen
```

The script also warns when there is too little data (fewer than 10 fall sessions,
under 10 minutes of normal movement, missing `sit_down_hard` / `stairs`, or only
one person). With synthetic data those warnings fire, as they should: **issue #9
stays open until the physical recordings exist.**

## 4. AI health summary (#10)

- `GET /api/devices/{id}/summary` and `POST /api/devices/{id}/chat` answer in
  Bahasa Indonesia from the stored data.
- The prompt forbids diagnoses, disease names and medicines, tells the model to
  mention unhandled alerts first, and marks potentiometer readings as SIMULASI.
- Only numbers and the elder's display name go to Gemini; no device id, IP or
  location.
- Without a key, or when Gemini fails, a rule-based summary in the same format
  is returned and labelled "Ringkasan otomatis" / "Jawaban otomatis, bukan dari
  AI", so a fixed sentence is never presented as AI.
- Model: `gemini-3.8-flash` by default (`JAGSI_GEMINI_MODEL`), following Google's
  guidance that new projects use 3.8 Flash or 3.5 Flash-Lite.

Screenshots (`docs/evidence/week7-ai-summary.png`, `docs/evidence/week7-chat.png`)
show the dashboard with telemetry delivered through the Event Grid webhook and
the rule-based answers, since no key was available. Icons render as text names
only because the screenshot environment cannot load Google Fonts.

## 5. One more Week 6 leftover fixed

`npm ci` still failed after Week 6's lockfile regeneration (`@emnapi/core`,
`@emnapi/runtime` and `@emnapi/wasi-threads` missing). The lockfile is now in
sync and CI uses `npm ci` again.
