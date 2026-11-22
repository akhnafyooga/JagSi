# JagSi watch firmware: Wokwi end product (v0.2.0)

Issues: #20 (R01 to R03), #5. Plan: `docs/wokwi-team-requirements.md` sections 4 and 6.
Baseline: `feat/week6-integration` at `b6278df`. The MQTT payload format is unchanged
(`docs/mqtt-contract.md`), so the existing backend, tools and dashboard keep working.

```
firmware/jagsi-watch/
  sketch.ino         ESP32 firmware (Arduino C++)
  motion_window.h    30-sample ring buffer with per-sample gap tracking
  diagram.json       Wokwi circuit (ESP32 DevKitC V4)
  libraries.txt      Wokwi libraries
firmware/test/
  test_motion_window.cpp   host unit tests (90 checks)
```

## What changed from 0.1.0

| Change | Why |
|---|---|
| `TOPIC_BASE` is `jagsi/abal/demo-wflx1f/v1/` | Shared demo prefix from plan section 4. Set the same value in the backend `JAGSI_TOPIC_BASE`. Change both if the team picks another token. |
| `dropped` = gaps still inside the current window | Plan section 6. Before, the counter reset after each publish, so the next two overlapping windows went out with the gap inside them and `dropped=0`. Now a gapped window stays rejected until the gap ages out (29 clean samples later). |
| Drift-free 10 Hz scheduler | Samples stay on a 100 ms grid. A stall longer than 150 ms is recorded as missed samples (rounded). |
| DS18B20 read by cached address, async conversion | No OneWire bus search inside the 100 ms loop (plan section 6). |
| Motion values clamped to +/-8 g and +/-500 deg/s | Bounds the JSON. Measured worst case is 1,394 bytes against the 1,600-byte serializer buffer and the 2,048-byte MQTT buffer. Oversized JSON is never truncated, it is not sent and a line is printed. |
| `[HEALTH]` line every 10 s | Loop time, windows sent, gapped windows, missed samples, largest motion payload. Use it as evidence for R02. |
| Serial Monitor commands | `scenario stable / rising_hr / falling_spo2 / rising_temperature / off`, `status`, `sos`. For the section 13 demo. |

### About the scenarios

A scenario replaces the potentiometer and DS18B20 values with a 2-minute linear ramp
from 75 bpm / 98 % / 36.6 C, then holds. Shape and noise follow
`backend/demo/train_trends.py`, which means the trend model has seen this exact pattern
during training. Present it as a synthetic demo of the pipeline, not as evidence of
model accuracy. All values keep `sim: true`. Type `scenario off` to return to the
potentiometers.

## Run it on Wokwi

1. Open https://wokwi.com/projects/new/esp32 and sign in (needed to save and to add a
   second file).
2. Replace `sketch.ino` with this `sketch.ino`.
3. Editor tab menu (small arrow right of the tabs) > New file... > `motion_window.h`,
   paste this `motion_window.h`.
4. Replace `diagram.json` with this `diagram.json`.
5. Library Manager > + > add PubSubClient, ArduinoJson, Adafruit MPU6050, Adafruit
   Unified Sensor, OneWire, DallasTemperature (same list as `libraries.txt`).
6. Press Run. Expected Serial Monitor output, in order:
   `[SENSOR] MPU6050 OK`, `[SENSOR] DS18B20 OK`, `[WIFI] connected`,
   `[MQTT] connected`, `[MQTT] -> .../status`, then telemetry every 2 s and a
   `[MOTION]` line every 5th window (about 1,000 to 1,100 bytes at rest).
7. Save the project and share the URL with the team (R01 evidence).

The free Wokwi tier compiles in a shared build queue, so the first build can take
30 seconds or more.

## Pin map (verification checklist)

| Part | ESP32 pin | Notes |
|---|---|---|
| MPU6050 SDA / SCL | 21 / 22 | VCC 3V3, GND |
| DS18B20 DQ | 4 | 4.7 kOhm pull-up to 3V3 |
| Pot "Heart rate" | 34 | 40 to 180 bpm |
| Pot "SpO2" | 35 | 80 to 100 % |
| Pot "Battery" | 32 | compatibility field, label as simulated in the UI |
| SOS button | 18 to GND | INPUT_PULLUP, 50 ms debounce |
| Alert LED + 220 Ohm | 26 | blinks until the backend sends `ack_alert` |

## Demo checks (plan sections 13 and 14)

| Check | How |
|---|---|
| Potentiometers change incoming values | Turn a pot, watch `heart_rate` / `spo2` in telemetry or `/api/devices/jagsi-watch-01/telemetry/latest` |
| Temperature changes | Click the DS18B20 during the simulation and move its slider |
| Device fall rule | Click the MPU6050, set acceleration X and Y to about 2 g (total above 2.5 g). One `fall_detected` event, 10 s cooldown. |
| ML path | Not proven by the slider. Use `backend/scripts/replay_ml_only.py` with Wokwi stopped (plan section 8). |
| Five SOS presses | Five unique `event_id`s; re-sent every 5 s until acked, max 5 attempts |
| Gap handling | `[HEALTH] gapped=` stays 0 in steady state. After an MQTT reconnect, windows print `dropped=N` until the gap ages out, then return to 0. |
| Trend scenarios | `scenario rising_hr` etc. Wait 2 minutes (60 readings) before calling `/progress`. |

## Watch the messages without the backend

HiveMQ web client (https://www.hivemq.com/demos/websocket-client/): connect, subscribe to
`jagsi/abal/demo-wflx1f/v1/#`.

The Python tools in `tools/` still default to `jagsi/abal/v1`. To use them with the demo
prefix, change `TOPIC_BASE` in `tools/jagsi_schema.py` to `jagsi/abal/demo-wflx1f/v1`
(no trailing slash there).

## Host tests

```bash
g++ -std=c++17 -Wall -Wextra -I firmware/jagsi-watch firmware/test/test_motion_window.cpp -o /tmp/t && /tmp/t
# 90 checks, 0 failures
```

## Verified on 22 November 2026

Compiled and run in Wokwi (anonymous ESP32 project, motion_window.h inlined because an
unsaved project cannot hold a second file; code otherwise identical, checked by SHA-256).

| Item | Observed |
|---|---|
| Compile on Wokwi ESP32 toolchain | OK, firmware banner 0.2.0 |
| Sensors | `MPU6050 OK`, `DS18B20 OK (async, cached address)`, temp 36.62 C |
| Wi-Fi / MQTT | Connected to broker.hivemq.com, status 168 B, telemetry 239 to 241 B |
| Motion window at rest | 566 to 567 B |
| Gap aging | Reconnect stall of ~3 s gave `dropped=30` on windows 3 to 5, then `dropped=0` once the gap left the window |
| SOS (`sos` command) | `manual_sos` event published, 257 B, event_id `jagsi-watch-01-<boot>-1` |
| Host tests | 90 checks, 0 failures; sketch type-checks clean with `-Wall -Wextra` |

Not yet verified: backend receipt and scoring with this prefix, ack round trip, five
physical button presses, full-speed steady state. These belong to the joint run with
Rafi's backend.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `[MQTT] connected` then drops and reconnects repeatedly | Look at the Wokwi speed gauge. Below about 50 %, the device cannot send its keep-alive within the broker's 22 s in real time. Use desktop Chrome, close heavy tabs, keep the Wokwi tab in front. |
| Backend shows nothing | Prefix mismatch. Firmware `TOPIC_BASE` and backend `JAGSI_TOPIC_BASE` must be identical, trailing slash included. |
| Every window rejected | Check `[HEALTH] gapped=`. Right after (re)connect a few gapped windows are expected. If it never returns to 0, something blocks the loop (`max_loop_ms`). |
| Compile error about motion_window.h | The file is missing or misnamed in Wokwi. Name it exactly `motion_window.h`. |

## Limits

- All readings are simulated, including the DS18B20 inside Wokwi.
- The public broker has no authentication. Synthetic data only.
- Physical MAX30102, casing (#7) and Azure transport (#8) remain future work.
