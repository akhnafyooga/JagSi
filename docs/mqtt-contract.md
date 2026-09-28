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
| `accel_peak_g`     | number        | g     | biggest acceleration since the last message (input for fall ML, #9) |
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
| `ack_alert`    | `{"cmd":"ack_alert","event_id":"jagsi-watch-01-3a9f1c2e-1"}` | stops re-sending that event              |

## 4. Fall rule (temporary)

Until the ML model (#9) is ready, the firmware uses a simple rule:
**if the total acceleration |a| ≥ 2.5 g → `fall_detected`** (then waits 10 s before it can trigger again).
This is only a placeholder so the pipeline can be tested end-to-end.
