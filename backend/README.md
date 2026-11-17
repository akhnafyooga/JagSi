# JagSi backend

Two parts in one service:

- `ml/` — the fall classification model from issue #9 (training, features, inference)
- `app/` — the MQTT bridge and the API the caregiver dashboard reads (Week 6)

Week 7 added three things to `app/`:

- **Azure IoT Hub** (#8, `azure_iot.py`): with `JAGSI_INGEST=azure`, device messages
  arrive through Event Grid at `POST /api/ingest/eventgrid` and commands go out as
  IoT Hub direct methods. Setup: `docs/azure-setup.md`.
- **AI health summary and chat** (#10, `ai_summary.py`): Gemini when
  `GEMINI_API_KEY` is set, a rule-based summary in the same format when it is not.
- **Labelled recording** (#9, `recorder.py`): records real motion windows for
  `scripts/retune_threshold.py`. Protocol: `docs/recording-protocol.md`.

Week 8 added **real-time emergency notifications** (#13, `realtime.py` and
`WS /ws/alerts` in `main.py`): every new fall or SOS is pushed to the dashboard the
moment it is stored, and the caregiver's "Saya tangani" goes back on the same
socket, is stored, is forwarded to the watch as `ack_alert`, and closes the alert
on every other open dashboard.

The bridge is the piece that connects them: it subscribes to the device's MQTT
topics, stores telemetry, feeds motion windows to the classifier, and pushes
updates to the dashboard over server-sent events.

```
device --MQTT--> bridge --> SQLite --> FastAPI --SSE (telemetry)-------> Next.js dashboard
                    |                     \----WebSocket (alerts, ack)--/
                    +--> FallClassifier --> ALERT_EVENT
```

SSE stays for telemetry (one direction, reconnects by itself). Alerts get a
WebSocket because the caregiver has to answer them.

## Setup

```bash
cd backend
pip install -r requirements-dev.txt
```

Versions are pinned. The trained artifact in `ml/artifacts/` was pickled by
scikit-learn 1.7.2 and loading it under a different minor version is not guaranteed
to score identically.

## Running it

Three terminals. First a broker, because the public one is unreliable and readable
by anyone:

```bash
python3 scripts/dev_broker.py --port 1883      # needs: pip install amqtt
```

Then the backend:

```bash
JAGSI_MQTT_HOST=127.0.0.1 uvicorn app.main:app --reload --port 8000
```

Then either Wokwi (point `MQTT_HOST` in `sketch.ino` at your machine) or the fake
device, which publishes the same payloads:

```bash
python3 ../tools/fake_device.py --host 127.0.0.1 --device-id jagsi-watch-01 --walking
python3 ../tools/fake_device.py --host 127.0.0.1 --device-id jagsi-watch-01 --fall-at 5
```

Check it is working:

```bash
curl -s localhost:8000/api/health | python3 -m json.tool
```

`bridge.connected` must be true and `telemetry` must be climbing.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/health` | bridge state, counters, active model threshold |
| GET | `/api/devices` | known devices and last contact |
| GET | `/api/devices/{id}/telemetry/latest` | newest reading, already shaped into dashboard cards |
| GET | `/api/devices/{id}/telemetry/history?limit=60` | recent readings for the charts |
| GET | `/api/alerts?limit=20` | recent alerts, newest first |
| POST | `/api/alerts/{alert_id}/ack` | acknowledge; stops the device re-sending |
| POST | `/api/devices/{id}/command` | `ping`, `set_interval`, `set_motion`, `ack_alert` |
| GET | `/api/stream` | server-sent events: telemetry, alert, alert_ack, status |
| WS | `/ws/alerts` | emergency alerts pushed instantly; send `{"type":"ack","alert_id":...}` to handle one (#13) |
| POST | `/api/ingest/eventgrid?key=...` | Azure mode only: IoT Hub messages from Event Grid |
| GET | `/api/devices/{id}/summary?refresh=false` | AI health summary in Bahasa Indonesia, cached 60 s |
| POST | `/api/devices/{id}/chat` | `{"question": "...", "history": [...]}`, answer about the stored data |
| GET | `/api/recording` | is a labelled recording open |
| POST | `/api/recording/start` / `stop` | `{"label": "walking", "subject": "s01"}` |

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `JAGSI_MQTT_HOST` | `broker.hivemq.com` | broker host |
| `JAGSI_MQTT_PORT` | `1883` | broker port |
| `JAGSI_DEVICE_ID` | `jagsi-watch-01` | default device for command topics |
| `JAGSI_DB_PATH` | `backend/data/jagsi.db` | SQLite file |
| `JAGSI_MODEL_PATH` | `backend/ml/artifacts/fall_clf.joblib` | trained artifact |
| `JAGSI_ENABLE_CLASSIFIER` | `true` | `false` runs the API without scoring |
| `JAGSI_FALL_THRESHOLD` | unset | overrides the artifact's threshold, see below |
| `JAGSI_DUPLICATE_WINDOW_S` | `10` | suppress an ML alert this soon after a device alert |
| `JAGSI_ML_COOLDOWN_S` | `15` | minimum gap between two ML alerts for one device |
| `JAGSI_CORS_ORIGINS` | `http://localhost:3000,...` | comma separated; also the only origins allowed to open `/ws/alerts` |
| `JAGSI_INGEST` | `mqtt` | `azure` switches to IoT Hub + Event Grid (no MQTT connection) |
| `JAGSI_IOTHUB_HOSTNAME` | unset | azure mode: `<hub>.azure-devices.net` |
| `JAGSI_IOTHUB_POLICY` | `service` | azure mode: shared access policy for direct methods |
| `JAGSI_IOTHUB_POLICY_KEY` | unset | azure mode: that policy's key |
| `JAGSI_EVENTGRID_KEY` | unset | azure mode, required: shared secret in the webhook URL |
| `GEMINI_API_KEY` | unset | enables Gemini; without it summaries are rule-based |
| `JAGSI_GEMINI_MODEL` | `gemini-3.8-flash` | Gemini model id |
| `JAGSI_SUMMARY_CACHE_S` | `60` | how long a summary is reused |
| `JAGSI_ELDER_NAME` | `Ibu Sari` | name used in summaries (no device id is sent to Gemini) |
| `JAGSI_RECORDINGS_DIR` | `backend/data/recordings` | where labelled recordings are written |

## Known issue: the decision threshold

The artifact carries a threshold of **0.11**, which flags ordinary walking as a fall
about 96% of the time. Measure it yourself:

```bash
python3 scripts/validate_on_device_windows.py --windows 200
```

Full numbers and what closing this requires are in `docs/week6-validation.md`.
`JAGSI_FALL_THRESHOLD` exists so the threshold can be tested without retraining;
the artifact is deliberately left alone.

Week 7 adds the tooling to fix it with real data: record labelled sessions from
the physical watch (`docs/recording-protocol.md`), then

```bash
python3 scripts/retune_threshold.py --write-artifact ml/artifacts/fall_clf_retuned.joblib
```

It scores falls per session and false alerts the way the backend raises them,
picks a threshold that meets both targets, and never overwrites the deployed model.

## The alert WebSocket (#13)

```
server -> dashboard                         dashboard -> server
{"type":"hello","data":{"open_alerts":[..]}}  {"type":"ack","alert_id":"..."}
{"type":"alert","data":<alert>}               {"type":"ping"}
{"type":"alert_ack","data":{"alert_id","via"}}
{"type":"ack_result","data":{...}}
{"type":"ping"|"pong"} / {"type":"error",...}
```

- `hello` lists every alert nobody has handled yet, so a phone that reconnects
  after sleeping still sees an alert that fired meanwhile.
- `alert_ack` goes to every socket, whether the ack came from a socket or from
  `POST /api/alerts/{id}/ack`, so two caregivers never both rush to the same alert
  without knowing.
- Browsers do not apply CORS to WebSockets. The socket checks the `Origin`
  header against `JAGSI_CORS_ORIGINS` and refuses anything else (HTTP 403);
  otherwise any website the caregiver opens could connect and silence a fall alert.
- The server pings every 20 s and the dashboard every 25 s, so a dead connection
  is noticed and the dashboard reconnects (1 s, 2 s, 4 s ... up to 30 s).

## Tests

```bash
python3 -m pytest -q                      # 124 tests: ml/ and app/
python3 scripts/integration_check.py      # 22 checks, whole pipeline on a local broker
python3 scripts/eventgrid_check.py        # 17 checks, the same over Azure (Event Grid replay)
python3 scripts/alert_ws_check.py         # 13 checks, watch -> /ws/alerts -> ack -> watch (#13)
```

`scripts/integration_check.py` is the one to run after touching the firmware payload,
the bridge or the contract. It replays byte-identical device payloads through the real
bridge and asserts what ends up in the database.

## Layout

```
backend/
├── app/
│   ├── ai_summary.py    Gemini summary and chat, rule-based fallback (#10)
│   ├── azure_iot.py     Event Grid parsing, SAS tokens, direct methods (#8)
│   ├── bridge.py        message routing, window validation, classification, alerts
│   ├── recorder.py      labelled motion recording for re-tuning (#9)
│   ├── config.py        settings, all environment-overridable
│   ├── main.py          FastAPI endpoints, the SSE stream and /ws/alerts
│   ├── realtime.py      thread-safe fan-out of live events (#13)
│   ├── store.py         SQLite, table names follow the ERD
│   ├── vitals.py        telemetry row -> dashboard cards, with display bands
│   └── tests/
├── ml/                  issue #9; retune.py added in Week 7
└── scripts/
    ├── dev_broker.py                  local MQTT broker
    ├── integration_check.py           whole-pipeline check
    ├── eventgrid_check.py             the same over Azure Event Grid (#8)
    ├── alert_ws_check.py              real-time alerts end to end (#13)
    ├── retune_threshold.py            pick a threshold from real recordings (#9)
    └── validate_on_device_windows.py  model vs device-shaped windows
```
