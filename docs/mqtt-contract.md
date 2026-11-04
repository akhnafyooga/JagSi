# JagSi MQTT Contract (v1)

Issue: [#6 Program MQTT pub/sub data pipeline](https://github.com/akhnafyooga/JagSi/issues/6)
Status: Sprint 1 draft, tested on a public broker. In Sprint 2 (#8) the same topics and payloads move to Azure IoT Hub.

## 1. Broker (Sprint 1, development only)

| Item      | Value                          |
|-----------|--------------------------------|
| Host      | `broker.hivemq.com`            |
| Port      | `1883` (plain TCP, no TLS)     |
| Auth      | none                           |

> **Warning:** A public broker can be read by anyone. Only send **dummy data**, never real patient data. Real data will go through Azure IoT Hub with device certificates (#8).

## 2. Topic tree

All topics start with the base `jagsi/abal/v1/{device_id}/`.

| Topic                                  | Direction      | QoS | Retained | When                                  |
|----------------------------------------|----------------|-----|----------|---------------------------------------|
| `jagsi/abal/v1/{device_id}/telemetry`  | device → cloud | 0   | no       | every 2 s (changeable with `set_interval`) |
| `jagsi/abal/v1/{device_id}/motion`     | device → cloud | 0   | no       | every 1 s, a 3 s window of raw samples for the fall model |
| `jagsi/abal/v1/{device_id}/event`      | device → cloud | 0*  | no       | SOS button pressed / possible fall    |
| `jagsi/abal/v1/{device_id}/status`     | device → cloud | 0   | **yes**  | on connect, on `ping`; LWT = offline  |
| `jagsi/abal/v1/{device_id}/cmd`        | cloud → device | 1 (subscribe) | no | commands from backend / dashboard |

\* The PubSubClient library can only publish with QoS 0. To make sure an emergency is not lost, the
device **re-sends an event every 5 s (max 5 times) until the cloud sends `ack_alert`**. Events that
happen while offline are kept and sent after reconnecting.

Subscribe to everything from all devices: `jagsi/abal/v1/+/#`

`device_id` = `WEARABLE_DEVICE.device_id` in the ERD (default in firmware: `jagsi-watch-01`).

## 3. Payloads (JSON, UTF-8)

### 3.1 `telemetry` → table `TELEMETRY_DATA`

```json
{
  "device_id": "jagsi-watch-01",
  "seq": 42,
  "ts": "2026-09-28T12:00:00Z",
  "uptime_ms": 84000,
  "heart_rate": 78,
  "spo2": 97.0,
  "body_temperature": 36.6,
  "accel": { "x": 0.0, "y": 0.0, "z": 1.0 },
  "gyro":  { "x": 0.0, "y": 0.0, "z": 0.0 },
  "accel_peak_g": 1.0,
  "battery_level": 87,
  "sim": true
}
```

| Field              | Type          | Unit  | ERD column / note                                             |
|--------------------|---------------|-------|---------------------------------------------------------------|
| `device_id`        | string        | –     | `device_id` (FK)                                              |
| `seq`              | int           | –     | counter per boot; backend makes `telemetry_id` (e.g. UUID)     |
| `ts`               | string / null | UTC   | `timestamp` (ISO 8601). `null` if NTP time not synced yet → backend uses receive time |
| `uptime_ms`        | int           | ms    | time since device boot                                        |
| `heart_rate`       | int / null    | bpm   | `heart_rate`                                                  |
| `spo2`             | number / null | %     | `spO2`                                                        |
| `body_temperature` | number / null | °C    | `body_temperature`; `null` if sensor not found                |
| `accel`            | object        | g     | last accelerometer reading (motion vector)                    |
| `gyro`             | object        | °/s   | last gyroscope reading (motion vector)                        |
| `accel_peak_g`     | number        | g     | biggest acceleration since the last message. **Display and the fallback rule only, not an ML input** (see 3.5) |
| `battery_level`    | int           | %     | goes to `WEARABLE_DEVICE.battery_level`                       |
| `sim`              | bool          | –     | `true` = values come from the Wokwi simulation                |

### 3.2 `event` → table `ALERT_EVENT`

```json
{
  "device_id": "jagsi-watch-01",
  "event_id": "jagsi-watch-01-3a9f1c2e-1",
  "ts": "2026-09-28T12:00:05Z",
  "uptime_ms": 89000,
  "alert_type": "manual_sos",
  "status": "unresolved",
  "attempt": 1,
  "accel_peak_g": 1.0,
  "vitals": { "heart_rate": 78, "spo2": 97.0, "body_temperature": 36.6 }
}
```

| Field          | Type   | ERD column / note                                                        |
|----------------|--------|--------------------------------------------------------------------------|
| `event_id`     | string | `alert_id`. Unique; the same id is kept when the event is re-sent        |
| `alert_type`   | string | `alert_type`: `manual_sos` = "Manual SOS", `fall_detected` = "Fall Detected" |
| `status`       | string | `status`: always `unresolved` from the device                            |
| `attempt`      | int    | 1 = first send, 2..5 = re-send (backend must ignore duplicates by `event_id`) |
| `accel_peak_g` | number | biggest acceleration at the moment of the event                          |
| `vitals`       | object | last vital signs, so the caregiver sees them in the alert                |

### 3.3 `status` (retained)

```json
{ "device_id": "jagsi-watch-01", "state": "online", "fw": "0.1.0",
  "battery_level": 87, "rssi": -60, "ip": "10.10.0.2", "interval_ms": 2000 }
```

Last Will (sent by the broker if the device disconnects without saying goodbye):

```json
{ "device_id": "jagsi-watch-01", "state": "offline" }
```

### 3.4 `cmd` (device subscribes)

| Command        | Example                                                   | What the device does                     |
|----------------|-----------------------------------------------------------|------------------------------------------|
| `ping`         | `{"cmd":"ping"}`                                          | publishes `status` again                 |
| `set_interval` | `{"cmd":"set_interval","ms":5000}`                        | changes telemetry interval (1000–60000 ms) |
| `set_motion`   | `{"cmd":"set_motion","enabled":false}`                    | starts / stops the `motion` window stream (3.5) |
| `ack_alert`    | `{"cmd":"ack_alert","event_id":"jagsi-watch-01-3a9f1c2e-1"}` | stops re-sending that event              |

### 3.5 `motion` → input for the fall classifier (#9)

Why this topic exists: the `telemetry` message carries **one** accelerometer reading
per message. The classifier in `backend/ml/` needs a **whole window**:
`SAMPLE_RATE_HZ = 10`, `WINDOW_SECONDS = 3.0`, so `WINDOW_SIZE = 30` samples. Feeding
it `accel_peak_g` instead discards 29 of every 30 samples and makes 16 of its 18
features (jerk, free-fall duration, impact duration, post-impact inactivity, tilt
change, and the rest) impossible to compute. This topic carries the window the model
was actually trained on.

```json
{
  "device_id": "jagsi-watch-01",
  "seq": 12,
  "ts": "2026-11-04T12:00:03Z",
  "t0_ms": 84000,
  "sample_rate_hz": 10,
  "window_size": 30,
  "dropped": 0,
  "sim": true,
  "s": [
    [0.01, -0.02, 1.00, 0.5, -0.3, 0.1],
    [0.02, -0.01, 0.99, 0.4, -0.2, 0.0]
  ]
}
```

| Field            | Type   | Unit | Note                                                                 |
|------------------|--------|------|----------------------------------------------------------------------|
| `seq`            | int    | –    | window counter per boot                                              |
| `ts`             | string / null | UTC | time the window was published (end of the window)              |
| `t0_ms`          | int    | ms   | `uptime_ms` of the **oldest** sample, to line the window up with telemetry |
| `sample_rate_hz` | int    | Hz   | must be `10`; the backend rejects anything else                      |
| `window_size`    | int    | –    | must be `30`; must equal `len(s)`                                    |
| `dropped`        | int    | –    | samples the firmware missed since the last window. `> 0` means the 10 Hz spacing was broken, so the backend **skips** the window instead of scoring it |
| `s`              | array  | –    | exactly `window_size` rows, **oldest first**                         |
| `s[i]`           | array  | –    | `[ax, ay, az, gx, gy, gz]`. Accel in **g** (2 dp), gyro in **deg/s** (1 dp) |

Mapping to the model, in `backend/app/bridge.py`:

```python
samples = [AccelSample(ax=r[0], ay=r[1], az=r[2], gx=r[3], gy=r[4], gz=r[5]) for r in msg["s"]]
result = classifier.predict_window(samples)   # -> is_fall, confidence, label
```

Field order in `s[i]` is positional and matches `AccelSample`'s field order in
`backend/ml/schema.py`. Arrays rather than objects keep the payload near 1.2 kB; the
same window written as objects with named keys exceeds the 2 kB MQTT buffer.

Traffic cost: roughly 1.2 kB every second per device. The backend can stop the stream
with `{"cmd":"set_motion","enabled":false}` when no classifier is running.

## 4. Fall detection: two layers

There are now two detectors, on purpose, and they are not interchangeable.

| Layer | Where | Rule | Role |
|-------|-------|------|------|
| Device rule | `sketch.ino`, `checkFall()` | total acceleration \|a\| ≥ 2.5 g, 10 s cooldown | **Fallback.** Fires in under 100 ms and still works when Wi-Fi or the backend is down. Publishes `event` with `alert_type: fall_detected` |
| ML classifier | `backend/app/bridge.py` + `backend/ml/` | RandomForest over 18 features of a 30-sample window, threshold 0.11 | **Primary.** Catches falls the threshold misses and is the path the project's accuracy targets refer to |

The device rule is deliberately kept rather than removed. A wearable that only alerts
when the cloud is reachable is not an emergency device.

Duplicate suppression: when both layers fire for the same fall, two alerts reach the
caregiver. The backend therefore suppresses an ML alert if a device `event` for the
same `device_id` arrived within the last 10 seconds, and records which layer won in
`ALERT_EVENT.source` (`device_rule` or `ml`).
