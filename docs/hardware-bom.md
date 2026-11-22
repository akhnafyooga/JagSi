# JagSi Hardware Bill of Materials (v1)

Issue: Week 6, Sprint 2 — finalize sensor specification
Status: **Frozen for the Wokwi simulation.** The physical build column is a plan, not a result.

This document is the single source of truth for which sensors JagSi uses, on which
pins, at which rate, and which readings are real versus simulated. It exists because
two earlier documents disagreed:

| Document | What it claimed |
|----------|-----------------|
| Week 2 worksheet, project breakdown | "Interfacing ESP32 with **MAX30102** and MPU6050 sensors" |
| Week 4 report, Issue #6 | MPU6050 + **DS18B20**, with heart rate and SpO2 "simulated" |

Both were partly right. The Week 2 plan describes the **physical** wearable. The Week 4
report describes what was actually buildable in **Wokwi**, which has no MAX30102 part.
This BOM records both columns side by side so the gap is explicit instead of implied.

## 1. Component list

| # | Component | Measures | ESP32 pin | Bus / mode | Sampling | Wokwi | Physical build |
|---|-----------|----------|-----------|-----------|----------|-------|----------------|
| 1 | MPU6050 | Accelerometer (g) + gyroscope (deg/s) | SDA 21, SCL 22 | I2C @ 3V3 | **10 Hz** | Real part (`wokwi-mpu6050`) | Same part, no change |
| 2 | DS18B20 | Body temperature (°C) | GPIO 4 | OneWire, 4.7 kΩ pull-up to 3V3 | 1 Hz | Real part (`wokwi-ds18b20`) | Same part, no change |
| 3 | MAX30102 | Heart rate (bpm) + SpO2 (%) | SDA 21, SCL 22 | I2C @ 3V3 | 10 Hz (planned) | **Not available.** Stood in by two potentiometers on GPIO 34 (HR) and GPIO 35 (SpO2) | Required purchase |
| 4 | Push button | Manual SOS | GPIO 18 | `INPUT_PULLUP`, button to GND, 50 ms debounce | Interrupt-style polling | Real part | Momentary tactile switch |
| 5 | LED + 220 Ω | Unacknowledged-alert indicator | GPIO 26 | Digital out | Blink 250 ms | Real part | Same, or vibration motor |
| 6 | Battery monitor | Battery level (%) | GPIO 32 | ADC1_CH4, 12-bit | On each sample | Potentiometer stand-in | Resistor divider on LiPo |

Board: `board-esp32-devkit-c-v4` (Arduino core). ADC resolution set to 12 bit (0–4095).

### Why GPIO 34, 35 and 32 specifically

All three are ADC1 channels. ADC2 cannot be read while Wi-Fi is active on the ESP32,
and this firmware holds Wi-Fi up continuously for MQTT, so every analog input must sit
on ADC1. GPIO 34 and 35 are additionally input-only, which suits sensor stand-ins.

## 2. What is real and what is not

| Reading | Source in Wokwi | Trustworthy for the ML model? |
|---------|-----------------|-------------------------------|
| `accel.x/y/z`, `gyro.x/y/z` | MPU6050, simulated physics | **Yes.** This is the model's only input |
| `body_temperature` | DS18B20, settable in `diagram.json` (`"temperature": "36.6"`) | Yes, but constant unless changed by hand |
| `heart_rate` | Potentiometer, mapped linearly 40–180 bpm | **No.** Operator-controlled, carries no physiology |
| `spo2` | Potentiometer, mapped linearly 80–100 % | **No.** Same |
| `battery_level` | Potentiometer, mapped 0–100 % | No, display only |

Every telemetry message carries `"sim": true` so the backend and the dashboard can
label simulated values instead of presenting them as measurements. This matters for
FR 1, which promises heart rate and SpO2 monitoring: at Wokwi stage that requirement
is **structurally** satisfied (the field exists, flows, and is stored) but not
**physically** satisfied. The MAX30102 closes that gap.

## 3. Accelerometer range: one inconsistency to resolve

| Location | Value |
|----------|-------|
| `firmware/jagsi-watch/sketch.ino` | `mpu.setAccelerometerRange(MPU6050_RANGE_8_G)` |
| `backend/ml/schema.py` | `MPU6050_RANGE_G = 4.0  # typical configured accelerometer range` |

The firmware is configured for ±8 g, the ML schema documents ±4 g. The constant in
`schema.py` is currently unused by any code path, so this is a documentation defect
rather than a live bug, but it should be reconciled rather than left to drift.

Decision: **keep the firmware at ±8 g and correct `schema.py` to 8.0.** Reasoning: the
synthetic training set generates impact spikes of 2–4 g, and a real fall onto a hard
floor can exceed that. A ±4 g range would clip exactly the peaks the classifier relies
on. The cost is halved resolution, which the free-fall and impact features tolerate.

Known limitation to carry forward: because training impacts top out near 4 g, any real
impact well above that is outside the training distribution. This belongs in the model
card before the model is trusted on physical hardware.

## 4. Gyroscope and filter settings

| Setting | Value | Why |
|---------|-------|-----|
| Gyro range | `MPU6050_RANGE_500_DEG` | Fall rotation rates sit well inside 500 deg/s |
| Filter bandwidth | `MPU6050_BAND_21_HZ` | Above the 10 Hz sampling rate, below motor and handling noise |
| Accel range | `MPU6050_RANGE_8_G` | See section 3 |

## 5. Sampling and publishing rates

| Activity | Interval | Constant in firmware |
|----------|----------|----------------------|
| IMU sample | 100 ms (10 Hz) | `SENSOR_SAMPLE_MS` |
| DS18B20 read | 1000 ms | `TEMP_READ_MS` |
| Telemetry publish | 2000 ms, adjustable 1000–60000 ms | `DEFAULT_TELEMETRY_MS` |
| Motion window publish | 1000 ms hop, 3000 ms window | `MOTION_HOP_MS`, `MOTION_WINDOW_SIZE` |
| Alert re-send until ack | 5000 ms, max 5 attempts | `ALERT_RESEND_MS` |

The 10 Hz IMU rate is not a free choice. `backend/ml/schema.py` fixes
`SAMPLE_RATE_HZ = 10` and `WINDOW_SECONDS = 3.0`, giving `WINDOW_SIZE = 30`. The
firmware must sample at exactly this rate or the model's features become meaningless.
See `docs/mqtt-contract.md` section 3.5 for the window payload.

## 6. Procurement list for the physical prototype

| Item | Qty | Note |
|------|-----|------|
| ESP32 DevKit C v4 | 1 | Same board as simulated |
| MPU6050 module | 1 | GY-521 breakout is fine |
| MAX30102 module | 1 | Closes the FR 1 gap |
| DS18B20, waterproof probe | 1 | Skin contact, so probe form factor over bare TO-92 |
| 4.7 kΩ resistor | 1 | DS18B20 OneWire pull-up |
| 220 Ω resistor | 1 | LED current limit |
| Momentary push button | 1 | SOS |
| LiPo 500 mAh + TP4056 charger | 1 | Not simulated; battery curve is a potentiometer today |
| Wrist strap and printed casing | 1 | Week 2 deliverable "portable wearable watch prototype" |

Items 8 and 9 are the only line items with no counterpart in the simulation at all.
Until they exist, the Week 2 deliverable "portable wearable watch prototype" remains
open regardless of firmware progress.
