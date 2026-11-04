# JagSi firmware (ESP32)

Issue: [#6 Program MQTT pub/sub data pipeline](https://github.com/akhnafyooga/JagSi/issues/6)

```
firmware/jagsi-watch/
├── sketch.ino       # ESP32 firmware (Arduino C++)
├── diagram.json     # Wokwi circuit
└── libraries.txt    # Wokwi libraries
docs/mqtt-contract.md           # topics + JSON payloads (read this first)
docs/test-results-issue-6.md    # what was tested and the results
tools/                          # Python tools for the "cloud side"
tests/                          # automated tests
```

## Circuit (Wokwi)

| Part                 | ESP32 pin   | Purpose                                   |
|----------------------|-------------|-------------------------------------------|
| MPU6050 (SDA / SCL)  | 21 / 22     | accelerometer + gyroscope, fall rule      |
| DS18B20 (DQ) + 4.7 kΩ pull-up | 4  | body temperature                          |
| Potentiometer "Heart rate" | 34    | simulated heart rate 40–180 bpm (MAX30102 stand-in) |
| Potentiometer "SpO2" | 35          | simulated SpO₂ 80–100 % (MAX30102 stand-in) |
| Potentiometer "Battery" | 32       | simulated battery 0–100 %                 |
| Push button "SOS"    | 18 → GND    | manual SOS                                |
| Red LED + 220 Ω      | 26          | blinks while an alert waits for an ack    |

## Run it on Wokwi

1. Open <https://wokwi.com/projects/new/esp32>.
2. Paste `sketch.ino` into **sketch.ino** and `diagram.json` into **diagram.json**.
3. Open **Library Manager** → **+** and add: PubSubClient, ArduinoJson, Adafruit MPU6050,
   Adafruit Unified Sensor, OneWire, DallasTemperature (or create `libraries.txt` with the same list).
4. Press ▶. The Serial Monitor shows `[MQTT] connected` and `[MQTT] -> .../telemetry`.
5. To test: press the **SOS** button, or click the MPU6050 and move acceleration X and Y to 2 g (= a fall).

## Watch the messages

**Option A – browser:** open <https://www.hivemq.com/demos/websocket-client/>, connect, and subscribe to `jagsi/abal/v1/#`.

**Option B – Python monitor** (checks every message against the contract, can save CSV and auto-ack alerts):

```bash
cd tools
pip install -r requirements.txt
python mqtt_monitor.py --ack --csv-dir logs
```

Send a command to the device:

```bash
python mqtt_monitor.py --device jagsi-watch-01 --cmd '{"cmd":"set_interval","ms":5000}'
```

No Wokwi? Run a fake watch instead: `python fake_device.py --sos-at 3 --fall-at 5`

## Run the tests

```bash
pip install -r tools/requirements.txt pytest
sudo apt install mosquitto      # only needed for the end-to-end test
python -m pytest tests
```

## Next steps

- Sprint 2 (#8): change the broker to Azure IoT Hub (TLS + device authentication).
- #5 / #7: replace the heart rate + SpO₂ potentiometers with the real MAX30102 on the physical prototype.
- #9: replace the 2.5 g fall rule with the ML model.
