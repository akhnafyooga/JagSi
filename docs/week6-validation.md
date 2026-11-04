# Week 6 validation results

What was run, what passed, and one result that changes a conclusion from Week 5.

All commands below are reproducible. Nothing here is a screenshot of a thing working
once; each is a script that re-runs and either passes or fails.

## 1. Firmware window buffer, 80 checks

```
g++ -std=c++17 -Wall -Wextra -I firmware/jagsi-watch \
    firmware/test/test_motion_window.cpp -o /tmp/test_motion_window && /tmp/test_motion_window
```

```
test_not_full_until_capacity
test_first_window_is_chronological
test_wraparound_keeps_newest_oldest_first
test_all_axes_survive_the_round_trip
test_reset_clears_the_window
test_capacity_matches_ml_schema

80 checks, 0 failures
```

The ring buffer was moved out of `sketch.ino` into `motion_window.h` so it compiles on
a normal PC. Sample ordering is now covered by a test rather than by reading the code,
which matters because a buffer that returns the window in the wrong order still
produces a confident classification, just a wrong one.

## 2. Firmware-to-model contract, 15 tests

```
cd backend && python3 -m pytest app/tests/test_window_contract.py -q
15 passed
```

Covers both directions: a valid window parses into 30 `AccelSample`s with the axes in
the right order and all 18 features finite, and an invalid one is refused. Refusals
tested: wrong sample rate, wrong `window_size`, short window, dropped samples, a row
missing an axis, a non-numeric value, and a plain `telemetry` message.

That last one is the regression test for the actual defect: **a telemetry message was
what the pipeline used to feed the model.**

## 3. Whole pipeline, 22 checks

```
cd backend && python3 scripts/integration_check.py
22 checks, 22 passed, 0 failed
```

Runs a throwaway MQTT broker, the real `Bridge`, and payloads byte-identical to the
firmware's. Covers status upsert, telemetry persistence, a null device clock falling
back to server time, window scoring, window rejection, an ML alert with its
confidence, overlapping windows not producing an alert storm, a device event being
acknowledged, re-sends not creating duplicates, and a Last Will not wiping known
device fields.

## 4. Frontend, 22 tests

```
cd frontend && npx vitest run
Test Files  3 passed (3)
     Tests  22 passed (22)
```

`npx tsc --noEmit` is clean. `npm run lint` reports only the two pre-existing font
warnings in `app/layout.tsx`.

## 5. Live dashboard

`docs/evidence/dashboard-live.png` is the dashboard rendering telemetry that travelled
the full path: fake device to MQTT to the bridge to SQLite to the API to the browser
over server-sent events. The card header shows a LIVE chip and the last update time,
heart rate and SpO2 carry a SIM badge, and body temperature does not, because DS18B20
is a real part in Wokwi and the other two are potentiometers.

The icons render as their text names in that screenshot because the capture
environment cannot reach Google Fonts. They display normally in a browser.

---

## The finding that matters

**The fall classifier flags ordinary walking as a fall.**

Week 5 reported recall 0.985 and precision 0.914 against the issue #9 targets of 0.95
and 0.90. Those figures were measured on windows produced by `ml/synth_data.py`, the
same module that produced the training data. That measures how well the model fits its
own generator, not how it behaves on what the watch publishes.

Re-measured against windows shaped the way the firmware sends them:

```
cd backend && python3 scripts/validate_on_device_windows.py --windows 200
```

| Scenario | Windows | Flagged as fall | Rate | Mean confidence |
|----------|---------|-----------------|------|-----------------|
| Still, sitting | 200 | 0 | 0.0% | 0.025 |
| **Walking** | 200 | **192** | **96.0%** | 0.149 |
| **Sit-to-stand** | 200 | **107** | **53.5%** | 0.108 |
| Fall | 200 | 200 | 100.0% | 0.980 |

```
recall      1.000   (target: >= 0.95)   PASS
precision   0.401   (target: >= 0.90)   FAIL
confusion   TP 200  FN 0  FP 299  TN 301
```

Windows arrive once per second, so at this precision a device would raise roughly
**1,800 false alerts per hour** while its wearer is simply walking around. The
backend's cooldown collapses a burst into one alert, but it does not change the rate:
a caregiver would be woken every fifteen seconds, and would switch the app off within
a day. A fall detector that cries wolf is not safer than no fall detector; it is worse,
because it trains the caregiver to ignore it.

### Cause

The stored decision threshold is **0.11**, tuned during training to reach the recall
target. The two classes are in fact well separated on these windows, walking averages
0.149 confidence and falls average 0.980, so the threshold is the whole problem:

| Threshold | Walking flagged | Sit-to-stand flagged | Fall recall | Precision |
|-----------|-----------------|----------------------|-------------|-----------|
| 0.11 (stored) | 99.3% | 58.7% | 1.000 | 0.388 |
| 0.20 | 0.0% | 0.0% | 1.000 | 1.000 |
| 0.30 | 0.0% | 0.0% | 1.000 | 1.000 |
| 0.50 | 0.0% | 0.0% | 1.000 | 1.000 |

### What was changed, and what was deliberately not

Changed: the threshold can now be overridden at runtime with `JAGSI_FALL_THRESHOLD`,
and the active value appears in `/api/health`. The team can test a different value
without retraining.

**Not changed: the artifact still carries 0.11.** Picking a new threshold belongs with
whoever owns the model, and the number above must not be read as "0.20 is correct".
The walking and sit-to-stand generators used here are synthetic too. They were written
to match the firmware payload, not to be ground truth for human movement. All this
result establishes is that the model's precision collapses on motion the training
generator did not contain, and that 0.11 is too aggressive.

### What closing this properly requires

1. Record real MPU6050 data from the physical wearable: walking, stairs, sitting down
   hard, lying down deliberately, and supervised falls onto a mattress.
2. Re-tune the threshold against that set, with precision weighted as heavily as
   recall rather than recall alone.
3. Re-measure, and update `ml/model_card.md` with the operating point and the activities
   it was validated against.

Until step 3, issue #9 is not finished, whatever the synthetic metrics say.

---

## Two other defects found

### The CI pipeline has never run anything

`.github/workflows/main.yml` gates every Node step on:

```yaml
if: ${{ hashFiles('package.json') != '' }}
```

`package.json` is at `frontend/package.json`, not at the repository root. The condition
has therefore always been false, so lint and tests have been skipped on every push
since the workflow was added. The job reports green because it does nothing.

The Week 5 report also states that a guarded backend-test job was added to this
workflow. No such job exists on `main`, `feat/9-fall-ml-model`, `feat/6-mqtt-pipeline`
or `frontend`.

Fixed in this branch: the workflow now runs the frontend tests, the backend tests, and
the firmware test, each with the correct working directory.

### `npm ci` fails on the committed lockfile

```
npm error Missing: @emnapi/runtime@1.11.3 from lock file
```

`package-lock.json` is out of sync with `package.json`. This did not surface earlier
because the workflow uses `npm install` and, as above, never ran it. Run
`npm install` in `frontend/` and commit the regenerated lockfile.
