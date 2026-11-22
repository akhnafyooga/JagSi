# Test Results – Issue #6 (MQTT pub/sub data pipeline)

Date: 28 September 2026 · Tester: Rafi Busthami · Firmware: 0.1.0
Setup: ESP32 simulated on Wokwi → `broker.hivemq.com:1883` → web MQTT client (subscribed to `jagsi/abal/v1/+/#`)

## Results

| # | Test | Expected | Result |
|---|------|----------|--------|
| 1 | Firmware compiles (Arduino ESP32 core 3.3.12, and Wokwi) | no errors | ✅ Pass (75% flash, 15% RAM) |
| 2 | Device connects to Wi-Fi + MQTT and publishes `status` | retained `"state":"online"` | ✅ Pass |
| 3 | Telemetry every 2 s | valid JSON on `/telemetry`, `seq` increases | ✅ Pass – HR 78 bpm, SpO₂ 97.01 %, temp 36.63 °C, battery 87 % |
| 4 | Device disappears without saying goodbye | broker sends Last Will `"state":"offline"` | ✅ Pass (seen when the simulation froze) |
| 5 | Press SOS button | `/event` with `alert_type: manual_sos` | ✅ Pass |
| 6 | No ack → re-send | same `event_id`, `attempt` 1 → 2 after 5 s | ✅ Pass |
| 7 | Send `ack_alert` | device stops re-sending | ✅ Pass (no attempt 3) |
| 8 | Fall: MPU6050 set to X=2 g, Y=2 g, Z=1 g (total 3 g) | `/event` with `alert_type: fall_detected`, `accel_peak_g: 3` | ✅ Pass |
| 9 | `set_interval` 5000 ms | telemetry every 5 s + new `status` | ✅ Pass (gaps 5000 ms) |
| 10 | `ping` | device publishes `status` | ✅ Pass |
| 11 | All received payloads checked with `tools/jagsi_schema.py` | 0 invalid | ✅ Pass |
| 12 | Python tests (`pytest tests`): schema + fake device → local Mosquitto → monitor | all pass | ✅ 8 passed |

## Example messages received from the Wokwi device

```text
status    {"device_id":"jagsi-watch-01","state":"online","fw":"0.1.0","battery_level":87,"rssi":-61,"ip":"10.10.0.2","interval_ms":2000}
telemetry {"device_id":"jagsi-watch-01","seq":12,"ts":"2026-09-28T13:09:08Z","uptime_ms":34147,"heart_rate":78,"spo2":97.01,"body_temperature":36.63,"accel":{"x":0,"y":0,"z":1},"gyro":{"x":0,"y":0,"z":0},"accel_peak_g":1,"battery_level":87,"sim":true}
event     {"device_id":"jagsi-watch-01","event_id":"jagsi-watch-01-f79fcd88-1","ts":"2026-09-28T13:09:22Z","uptime_ms":48747,"alert_type":"manual_sos","status":"unresolved","attempt":1,...}
event     {... "event_id":"jagsi-watch-01-f79fcd88-1", ... "attempt":2 ...}          <- re-send (no ack yet)
cmd       {"cmd":"ack_alert","event_id":"jagsi-watch-01-f79fcd88-1"}                  <- no more re-sends
event     {"device_id":"jagsi-watch-01","event_id":"jagsi-watch-01-f79fcd88-2","ts":"2026-09-28T13:10:12Z","uptime_ms":98014,"alert_type":"fall_detected","status":"unresolved","attempt":1,"accel_peak_g":3,...}
```

Screenshots: `docs/evidence/wokwi-running.jpg`, `docs/evidence/wokwi-fall-ack.jpg`

## Notes / known limits

- **Heart rate and SpO₂ are simulated** with potentiometers, because Wokwi has no MAX30102 part. The real MAX30102 code is still to do (needs the physical sensor, issue #5/#7).
- **Body temperature uses a DS18B20**, because the MAX30102 only measures its own chip temperature, not body temperature.
- The Wokwi simulation runs slower than real time (about 50 %), so the device `ts` can be behind the real clock. The backend should also save its own "received at" time.
- The public broker has no password and anyone can read it → **dummy data only**. Sprint 2 (#8) moves this to Azure IoT Hub with device authentication.
- The fall rule (|a| ≥ 2.5 g) is temporary until the ML model (#9) is ready.
