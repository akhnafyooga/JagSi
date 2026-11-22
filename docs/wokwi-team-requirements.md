# JagSi Wokwi Implementation and Team Requirements

Version 1 · 18 November 2026 · Team ABAL

## 1 Purpose and delivery decision

This document aligns Akhnaf, Akmal and Rafi on a fully simulated JagSi demonstration. We will run ESP32 firmware in Wokwi, transmit simulated sensor readings through MQTT, classify motion and vital trends using models trained by the team, persist readings and results in Supabase, and show the evidence in the existing Next.js caregiver dashboard.

The deliverable is an implementation plan with reference code and acceptance checks. The new code below must pass integration tests before the team claims it is delivered. Public source was inspected on 18 November 2026. Cloud resources and new model training have separate acceptance gates.

### Agreed demo scope

- Wokwi simulates the ESP32, MPU6050, DS18B20, SOS button and potentiometers for heart rate and SpO2. All observations carry simulated provenance, including virtual temperature.
- Our existing Random Forest classifies motion windows. A second team-trained Random Forest classifies patterns in a recent vital-sign window. Caregiver wording comes from reviewed messages attached to model outputs.
- FastAPI and inference run on the presenting laptop. Supabase provides persistent cloud storage. The dashboard runs locally in the initial release. The laptop needs internet connectivity for Wokwi, the broker and cloud synchronization.
- Azure remains a future integration track. The selected demo uses Supabase. Physical sensor accuracy and clinical validity remain future evaluation work.
- The existing battery field remains a simulated compatibility field. The demo has no physical battery and the dashboard must label that field as simulated or hide it.

## 2 Baseline and ownership

Use commit `b6278df5fbc6444be805a0cb0970a5b24665981f` on `feat/week6-integration` as the reproducible implementation baseline. `main` currently contains documentation updates. Reports describe later WebSocket features, but their implementation is absent from the published branch list inspected for this plan. Inspect any newly published branch before integrating it.

The README identifies Rafi as group leader and Akhnaf and Akmal as members. Specialist assignments below follow the team's earlier report responsibilities. Estimates are planning ranges, with no deadline inferred.

| Person | GitHub account | Accountable work package | Complexity | Estimate |
| --- | --- | --- | --- | --- |
| Akhnaf Fawzan Yogatrisna | akhnafyooga | #20 firmware, Wokwi scenarios, fall classifier, trend-model training and evaluation | L4 high | 4–6 focused days |
| Rafi Busthami | RafiBusthami | #21 backend, Supabase schema, synchronization, inference API and integration lead | L4 high | 3–5 focused days |
| Akmal Rafli Fauzan | akmalraflifauzan | #22 dashboard, wireframe alignment, provenance labels, emergency UX and acceptance evidence | L3 medium | 2–4 focused days after API contracts |

L1 covers a local configuration change. L2 covers one component with an established interface. L3 covers several interfaces and failure handling. L4 covers timing, data integrity or model evaluation across components. Complexity reflects uncertainty as well as code volume.

### Work sequence and handoffs

1. Rafi establishes the integration branch, device ID, topic prefix and storage contract. Akhnaf and Akmal review those values before implementation.
2. Akhnaf proves virtual sensor values reach FastAPI, then delivers a model artifact, feature contract and held-out synthetic evaluation. Rafi builds cloud synchronization in parallel after the contract is fixed.
3. Rafi exposes cloud history and model inference, including missing-data and cloud-failure responses. Akmal connects the dashboard and records the complete demo.
4. Each owner opens a PR. Another member reviews the changed interface. Rafi integrates the three PRs and records the final tested commit.

## 3 Functional and acceptance requirements

| ID | Requirement | Owner | Acceptance evidence |
| --- | --- | --- | --- |
| R01 | Boot the shared Wokwi project with no physical parts | Akhnaf | Saved project URL, compile log and pin map |
| R02 | Sample motion at 10 Hz, send 30 samples oldest-first once per second | Akhnaf | Firmware contract tests and MQTT sample capture |
| R03 | Publish vitals every 2 seconds and accept SOS acknowledgments | Akhnaf | Five button presses and duplicate-delivery test |
| R04 | Reject malformed, non-finite and incorrectly timed motion windows | Akhnaf | Negative API/bridge tests and rejection counts |
| R05 | Execute the existing fall classifier and expose its active threshold | Akhnaf | ML alert source, confidence, artifact revision and health endpoint |
| R06 | Train and evaluate the owned vital-trend model reproducibly | Akhnaf | Training script, metrics, model card and independent session split |
| R07 | Persist telemetry, alerts and model results in Supabase | Rafi | SQL rows survive backend restart and replay adds no duplicates |
| R08 | Recover synchronization after a cloud outage | Rafi | Local backlog catches up in batches after reconnection |
| R09 | Serve observed-window statistics and model-based caregiver guidance | Rafi | Outputs trace back to stored timestamps and model version |
| R10 | Show live, stale, disconnected and simulated states explicitly | Akmal | Screenshots from each state |
| R11 | Show and acknowledge fall/SOS alerts on the dashboard | Akmal | Two-tab test, opt-in alarm test and measured delivery latency |
| R12 | Keep database credentials in backend environment variables | Rafi | Repository and frontend bundle review |
| R13 | Complete an end-to-end demo and negative tests | All, Akmal coordinates | Evidence directory and final checklist in section 14 |

Use the project's target of at most 5 seconds for an alert after backend receipt of the final required motion sample. Also report event-to-screen time from the start of the scripted event, which includes window formation. Do not substitute simulation clock time for wall-clock latency.

## 4 Architecture and data contracts

```text
Wokwi ESP32 or deterministic replay
  -> public MQTT development broker
  -> existing FastAPI bridge on laptop port 8000
     -> existing fall classifier
     -> local SQLite durable staging
     -> SSE live telemetry and alerts
  -> cloud mirror worker reads committed SQLite rows
     -> Supabase PostgreSQL
  -> FastAPI progress router reads Supabase
     -> JagSi trend classifier on laptop
     -> stored model output and reviewed caregiver message
  -> Next.js dashboard on laptop port 3000
```

SQLite supplies the durable local staging and existing API behavior. Supabase holds persistent cloud history and analysis. Keeping cloud writes out of the MQTT callback avoids blocking 10 Hz sampling and alert delivery. Cloud synchronization is eventual, with a normal target of 5 seconds. The progress endpoint returns an error when cloud data are unavailable. The UI must retain a visible error state.

### Shared configuration

| Setting | Example | Meaning |
| --- | --- | --- |
| Device ID | jagsi-watch-01 | Must match firmware and dashboard |
| Topic prefix | jagsi/abal/demo-TEAMTOKEN/v1/ | Replace TEAMTOKEN with one shared random suffix |
| Broker | broker.hivemq.com on 1883 | Development transport for synthetic data |
| MQTT suffixes | telemetry, motion, event, status, cmd | Subscribe only to the first four |
| HTTP API | http://127.0.0.1:8000 | Existing backend plus progress router |
| Dashboard | http://localhost:3000 | Listed CORS origin |
| Cloud source ID | one UUID per local SQLite database | Separates local row IDs across machines |

The topic suffix lowers accidental topic collisions. A public broker provides no device identity guarantee. Use synthetic values and no patient identities. Store cloud credentials only on Rafi's backend machine. Use TLS and authenticated ingestion before handling real personal data.

### Message shape

Keep `docs/mqtt-contract.md` from the baseline as the authoritative complete contract. `motion.s` contains exactly 30 arrays of `[ax, ay, az, gx, gy, gz]`. Acceleration uses g and rotation uses degrees per second. Firmware converts Adafruit library SI readings to those units. `sample_rate_hz=10`, `window_size=30`, `dropped=0` and `sim=true` must be present. `telemetry` contains one motion observation and vitals. It cannot replace a complete motion window for inference.

## 5 Prepare the shared checkout

Owner Rafi · Complexity L2

1. Install Git, Python 3.11 and Node.js 20 LTS with npm. Verify `git --version`, `py -3.11 --version`, `node --version` and `npm --version` in PowerShell.
2. Use a fresh directory beside any checkout that contains unfinished work. Run the commands below from the directory where you want the new checkout.
3. Set up the shared branch once. Team members clone that branch after Rafi pushes it. Individual changes use `codex/wokwi-ml`, `codex/cloud-inference` and `codex/dashboard-demo` branches created from it.

```powershell
git clone https://github.com/akhnafyooga/JagSi.git JagSi-demo
Set-Location JagSi-demo
git switch --detach b6278df5fbc6444be805a0cb0970a5b24665981f
git switch -c codex/wokwi-owned-ai
git push -u origin codex/wokwi-owned-ai
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv\Scripts\python.exe -m pip install -r tools/requirements.txt
.\.venv\Scripts\python.exe -m pip install "psycopg[binary]>=3.2,<4" python-dotenv
Set-Location frontend
npm install
npm run test
npm run lint
npx tsc --noEmit
npm run build
Set-Location ..
```

The baseline lockfile has a reported `npm ci` mismatch. Run `npm install` once, review the lockfile diff, commit the corrected lockfile, and then use `npm ci` for repeat installations and CI. Commit the tested additional dependency versions in a separate demo requirements file after the first successful install. Run backend tests from `backend` with `..\.venv\Scripts\python.exe -m pytest -q`.

## 6 Build the Wokwi circuit

Owner Akhnaf · Complexity L3

1. Open https://wokwi.com/projects/new/esp32 and sign in to save a team project.
2. Open `firmware/jagsi-watch/sketch.ino` in the checkout and copy its entire contents into Wokwi's `sketch.ino` tab.
3. Create a Wokwi file named `motion_window.h`. Copy the entire file of that name from the same checkout. This header implements the ring buffer and is required for compilation.
4. Replace Wokwi's `diagram.json` with the entire `firmware/jagsi-watch/diagram.json` file. Its ESP32 is the Wokwi DevKitC V4. The earlier 30-pin 3D illustration uses a different board outline. Identify connections by GPIO label.
5. Create `libraries.txt` and paste the entire baseline file. It lists PubSubClient, ArduinoJson, Adafruit MPU6050, Adafruit Unified Sensor, OneWire and DallasTemperature. Wokwi resolves supporting libraries. Resolve compile errors before running the circuit.
6. Update `TOPIC_BASE` in `sketch.ino` to the agreed prefix from section 4. Keep the trailing slash. Keep `DEVICE_ID` consistent. Configure the broker and port as shown in section 4.
7. Keep `WiFi.begin("Wokwi-GUEST", "", 6)` and the public gateway. The gateway can reach the public broker. Your local backend independently connects to that broker, so Wokwi never needs access to laptop localhost.
8. Press Run, open Serial Monitor and wait for Wi-Fi and MQTT connection messages. Wait at least 3 seconds of simulated time for the first complete motion window.
9. Save the project. Share its URL and final firmware commit with Rafi and Akmal.

The pinned checkout supplies complete firmware code, circuit JSON and header code. Copy all four files as a set. The following pin-by-pin table is the verification checklist for the imported circuit.

| Component terminal | Connect to | Check |
| --- | --- | --- |
| MPU6050 VCC and GND | ESP32 3V3 and GND | All grounds common |
| MPU6050 SDA and SCL | GPIO21 and GPIO22 | I2C address normally 0x68 |
| DS18B20 VCC and GND | 3V3 and GND | Virtual temperature input |
| DS18B20 DQ | GPIO4 | 4.7 kOhm resistor between DQ and 3V3 |
| Heart-rate potentiometer VCC, GND, SIG | 3V3, GND, GPIO34 | Firmware maps to 40–180 bpm |
| SpO2 potentiometer VCC, GND, SIG | 3V3, GND, GPIO35 | Firmware maps to 80–100 percent |
| Compatibility battery potentiometer | 3V3, GND, GPIO32 | Retained virtual input, label or hide in UI |
| SOS switch separate sides | GPIO18 and GND | INPUT_PULLUP, pressed is LOW |
| Alert LED anode | GPIO26 through 220 Ohm resistor | Cathode to GND |
| ESP32 serial TX and RX | Wokwi serial monitor RX and TX | Provided by imported circuit |

A mini breadboard may be added for presentation layout. Each five-hole strip on each side of the middle gap forms one node. Route power, GND, SDA and SCL to separate strips and preserve the table's electrical nets. The breadboard is optional electrically in Wokwi. Validate all nets after moving connections. A decorative breadboard with wires bypassing it must be described as layout only.

### Firmware adjustments and sampling checks

The baseline uses `mqtt.setBufferSize(2048)` and a separate motion serialization buffer. Record the largest motion message and verify that the publish succeeds. If messages exceed the MQTT limit, raise both limits consistently and test the maximum JSON length. Never silently truncate JSON.

The baseline has a local 2.5 g fall rule as well as backend ML. To prove the ML is operating, run an ML-only replay through the motion topic, as described in section 8. A manual slider jump that triggers the local rule proves that rule and alert transport.

The baseline tracks dropped samples since the last publish. Strengthen this so the count describes every gap still inside the current 30-sample window. A rejected window must remain rejected until the gap ages out. Use the ring-buffer timestamp test as a regression check. Also make all DS18B20 reads asynchronous if the sensor conversion blocks the 100 ms sampling loop.

## 7 Start and inspect the backend

Owner Rafi with Akhnaf · Complexity L3

Open PowerShell terminal A in the new checkout. Use the same prefix as the firmware.

```powershell
$env:JAGSI_TOPIC_BASE = 'jagsi/abal/demo-TEAMTOKEN/v1/'
$env:JAGSI_DEVICE_ID = 'jagsi-watch-01'
$env:JAGSI_MQTT_HOST = 'broker.hivemq.com'
$env:JAGSI_MQTT_PORT = '1883'
$env:JAGSI_ENABLE_CLASSIFIER = 'true'
Set-Location backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

1. Visit http://127.0.0.1:8000/api/health. Confirm `bridge.connected=true`, `classifier_loaded=true` and the active threshold. A loaded HTTP server alone does not prove MQTT or ML readiness.
2. Start Wokwi. Visit `/api/devices` and `/api/devices/jagsi-watch-01/telemetry/latest`. Confirm that the values change when you turn the potentiometers.
3. Inspect `motion_scored` and `motion_rejected` in health. Record any rejection reason and timing before proceeding.
4. Press SOS and inspect `/api/alerts?device_id=jagsi-watch-01`. Confirm one durable event ID despite retries.
5. Acknowledge an alert through the API below. Substitute the actual ID.

```powershell
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/alerts/ACTUAL_ALERT_ID/ack'
```

The baseline automatically acknowledges receipt back to the device when it stores a device event. Caregiver acknowledgment is a separate state transition. The LED stopping after durable receipt does not prove a caregiver handled the emergency. Keep the distinction in the presentation and UI.

### Required input validation changes

In `backend/app/bridge.py`, extend `parse_window` after numeric conversion with `math.isfinite` checks for all six axes. Reject bool values as numeric samples. In `_on_message`, require the payload device ID to equal the topic's device segment and the expected demo device. Add MQTT `on_connect` error reporting and payload size limits. The public broker still cannot authenticate publishers. Capture wrong-size, missing-axis, NaN, Infinity, dropped-sample and wrong-device test cases.

## 8 Verify and evaluate the fall model

Owner Akhnaf · Complexity L4

1. The artifact is `backend/ml/artifacts/fall_clf.joblib`. Use the pinned requirements. `ml.inference.FallClassifier.load()` and `predict_window()` are the normal inference entry points.
2. Run the existing feature, generator, inference and bridge contract tests. Run the firmware C++ ring-buffer tests if a C++17 compiler is available. Install the compiler before treating that gate as complete.
3. Run `backend/scripts/validate_on_device_windows.py --windows 200` from `backend`. Save the output and the artifact hash. The published baseline gives precision about 0.401 on firmware-shaped synthetic windows at threshold 0.11. The task remains open for real-sensor validation.
4. Choose a demonstration threshold using a separate synthetic tuning split. Record it with `JAGSI_FALL_THRESHOLD` in terminal A before restarting the backend. Report the synthetic nature of this operating point.
5. Create the small script below as `backend/scripts/replay_ml_only.py`. It uses the existing fake-device payload implementation while suppressing its local rule event. Run it as shown. The resulting alert must have `source=ml`.

```python
from pathlib import Path
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools"))
from dotenv import load_dotenv
load_dotenv(".env.demo")
import jagsi_schema
jagsi_schema.TOPIC_BASE = os.environ["JAGSI_TOPIC_BASE"].rstrip("/")
from fake_device import FakeDevice, parse_args

device = FakeDevice(parse_args([
    "--device-id", "jagsi-watch-01",
    "--count", "15", "--fall-at", "5",
]))
original_raise = device.raise_alert

def manual_only(kind, peak):
    if kind != "fall_detected":
        original_raise(kind, peak)

device.raise_alert = manual_only
device.run()
```

Before replay, stop Wokwi to avoid concurrent publishers for one device ID. The script loads the shared prefix from `.env.demo` and applies it to the existing topic helper before creating the fake device. Create `.env.demo` using section 10 first. Confirm captured MQTT topics match terminal A. Run `..\.venv\Scripts\python.exe scripts/replay_ml_only.py` from `backend`.

6. For final metrics, create independent scripted sessions for stillness, walking, abrupt sitting, deliberate lying down and impacts. Keep all overlapping windows from one session in one split. Record recall, precision, false alerts per hour, session counts and non-fall duration. Aim at the existing recall >=0.95 and precision >=0.90 targets on the held-out synthetic set. Report any miss.
7. Store model revision, source commit, feature order and threshold in the model card. The dashboard must display the actual model output and confidence. An impact slider demo alone cannot establish those targets.

## 9 Train the owned vital trend model

Owner Akhnaf · Complexity L4

This second model answers which simulated pattern appears in the last 60 telemetry readings. Classes are `stable`, `rising_hr`, `falling_spo2` and `rising_temperature`. They describe input patterns. Caregiver guidance asks for checking context and reviewing the observation. It makes no diagnosis or medication recommendation.

Create `backend/demo/` and save the following as `backend/demo/train_trends.py`. This is a reproducible synthetic prototype. Each generated session contributes one window, preventing overlapping samples from crossing the train/test split.

```python
from pathlib import Path
import hashlib
import json
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

LABELS = ["stable", "rising_hr", "falling_spo2", "rising_temperature"]
FEATURES = [f"{channel}_{stat}" for channel in ["hr", "spo2", "temp"]
            for stat in ["mean", "std", "delta", "range"]]

def features(values):
    values = np.asarray(values, dtype=float)
    if values.shape != (60, 3) or not np.isfinite(values).all():
        raise ValueError("Expected 60 finite [heart_rate, spo2, temperature] rows")
    output = []
    for column in values.T:
        output.extend([column.mean(), column.std(),
                       column[-10:].mean() - column[:10].mean(), np.ptp(column)])
    return np.asarray(output)

def train(output_dir):
    rng = np.random.default_rng(20261118)
    x, y = [], []
    for label in LABELS:
        for session in range(150):
            base = np.array([rng.uniform(65, 100), rng.uniform(95, 99),
                             rng.uniform(36, 37.2)])
            noise = rng.normal(size=(60, 3)) * [1.6, .18, .04]
            change = np.zeros(3)
            if label == "rising_hr":
                change[0] = rng.uniform(15, 35)
            elif label == "falling_spo2":
                change[1] = -rng.uniform(2.5, 7)
            elif label == "rising_temperature":
                change[2] = rng.uniform(.7, 1.8)
            values = base + noise + np.linspace(0, 1, 60)[:, None] * change
            x.append(features(values))
            y.append(label)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=.25, random_state=41, stratify=y)
    model = RandomForestClassifier(n_estimators=150, max_depth=8,
                                   random_state=41, class_weight="balanced")
    model.fit(x_train, y_train)
    predicted = model.predict(x_test)
    report = classification_report(y_test, predicted, output_dict=True)
    report["confusion_matrix"] = confusion_matrix(
        y_test, predicted, labels=LABELS).tolist()
    report["labels"] = LABELS
    report["provenance"] = "synthetic sessions, one window per session"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "trend_model.joblib"
    joblib.dump({"model": model, "features": FEATURES,
                 "version": "synthetic-trends-v1", "rows": 60}, artifact)
    report["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    train(Path(__file__).resolve().parent / "artifacts")
```

Run from `backend` with `..\.venv\Scripts\python.exe -m demo.train_trends`. Save the metrics and artifact hash. Set an initial synthetic macro-F1 gate of 0.85, then test noisier sessions, mixed trends, sudden steps and missing data separately. The code above creates only single-pattern synthetic sessions. Predictions on mixed or real sessions require further evaluation. Add low-confidence abstention and show unavailable status when input coverage fails.

The new model is trained by the team and inference runs locally. The recommendation text in section 11 is deterministic and can be reviewed by all three members. Generating free-form medical advice is outside this demo's acceptance criteria.

## 10 Create Supabase cloud storage

Owner Rafi · Complexity L3

1. Sign in at https://supabase.com and create a Free project in the team's organization. Pick a nearby region and keep the database password in the team's approved secret store.
2. Wait for the project to become ready. Open SQL Editor and execute the complete migration below once. Save it as `backend/demo/schema.sql` in the repo.
3. Open the project Connect dialog, select the Session pooler and copy its PostgreSQL connection URI. Use the session pooler if the laptop network lacks IPv6. Replace the password placeholder with the actual URL-encoded password. Preserve the host, username, port and database supplied by Supabase.
4. Create `backend/.env.demo` locally. Add this exact filename to `.gitignore` before writing credentials. Set `JAGSI_CLOUD_DSN` to the URI plus SSL configuration as described below. Never add it to a `NEXT_PUBLIC_` variable.
5. Generate one UUID using `[guid]::NewGuid().ToString()` in PowerShell. Save it as `JAGSI_SOURCE_ID` in `.env.demo`. Use the same UUID after restarts of this database. Generate a new one if SQLite is deleted or replaced.
6. Share a sanitized `.env.demo.example` with names and placeholders. Keep real `.env.demo` local.

```sql
create table if not exists public.jagsi_demo_records (
  source_id uuid not null,
  kind text not null check (kind in ('telemetry', 'alert', 'cursor', 'analysis')),
  record_id text not null,
  device_id text not null,
  observed_at timestamptz not null,
  payload jsonb not null,
  primary key (source_id, kind, record_id)
);
create index if not exists jagsi_demo_device_time
  on public.jagsi_demo_records (source_id, device_id, kind, observed_at desc);
alter table public.jagsi_demo_records enable row level security;
revoke all on public.jagsi_demo_records from anon, authenticated;
```

The mirror connects through the server-side database URI. Browser users receive data through FastAPI. RLS and the revoked browser-role grants prevent direct anonymous table access. A public deployment will require application authentication and per-caregiver authorization before exposing history and acknowledgment endpoints.

```dotenv
JAGSI_CLOUD_DSN=postgresql://COPY_THE_SESSION_POOLER_URI?sslmode=require
JAGSI_SOURCE_ID=PASTE_YOUR_GENERATED_UUID
JAGSI_DB_PATH=data/jagsi.db
JAGSI_DEVICE_ID=jagsi-watch-01
JAGSI_TOPIC_BASE=jagsi/abal/demo-TEAMTOKEN/v1/
JAGSI_TREND_MODEL=demo/artifacts/trend_model.joblib
```

If the URI already has a query string, append `&sslmode=require`. Relative paths in this document assume the process working directory is `backend`. The topic variable must be present in the existing backend process too. Loading `.env.demo` in the mirror process does not change a different terminal's environment.

## 11 Reference backend extension code

Owner Rafi · Complexity L4

Create `backend/demo/cloud.py` with this complete code. It mirrors committed rows from the existing SQLite schema, resumes using a cloud cursor, updates alert acknowledgment state and exposes the progress endpoint. Run one mirror worker per source ID. The implementation batches writes and advances the cursor in the same PostgreSQL transaction. A failed batch rolls back and retries.

```python
import json
import logging
import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import joblib
import psycopg
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from psycopg.types.json import Jsonb
from demo.train_trends import features

load_dotenv(".env.demo")
router = APIRouter()
log = logging.getLogger("jagsi.cloud")
SOURCE = str(uuid.UUID(os.environ["JAGSI_SOURCE_ID"]))
DEVICE = os.getenv("JAGSI_DEVICE_ID", "jagsi-watch-01")
DB = Path(os.getenv("JAGSI_DB_PATH", "data/jagsi.db")).resolve()
MODEL = Path(os.getenv("JAGSI_TREND_MODEL", "demo/artifacts/trend_model.joblib"))

def connect():
    return psycopg.connect(os.environ["JAGSI_CLOUD_DSN"], connect_timeout=5)

def put(connection, kind, record_id, device_id, observed_at, payload):
    connection.execute(
        """insert into public.jagsi_demo_records
        (source_id, kind, record_id, device_id, observed_at, payload)
        values (%s, %s, %s, %s, %s, %s)
        on conflict (source_id, kind, record_id) do update set
        payload=excluded.payload, observed_at=excluded.observed_at""",
        (SOURCE, kind, str(record_id), device_id, observed_at, Jsonb(payload)))

def mirror_once():
    if not DB.exists():
        raise RuntimeError(f"Start the backend first; SQLite is missing at {DB}")
    with connect() as cloud:
        cloud.execute("set statement_timeout = '10s'")
        saved = cloud.execute(
            """select payload from public.jagsi_demo_records
            where source_id=%s and kind='cursor' and record_id='telemetry'""",
            (SOURCE,)).fetchone()
        cursor = int(saved[0]["last_id"]) if saved else 0
        local = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)
        local.row_factory = sqlite3.Row
        try:
            rows = local.execute(
                "select * from telemetry_data where telemetry_id>? "
                "and device_id=? order by telemetry_id limit 200",
                (cursor, DEVICE)).fetchall()
            alerts = local.execute(
                "select * from alert_event where device_id=?", (DEVICE,)).fetchall()
        finally:
            local.close()
        for row in rows:
            value = dict(row)
            value["simulated"] = True
            put(cloud, "telemetry", value["telemetry_id"], DEVICE,
                value["received_at"], value)
        for row in alerts:
            value = dict(row)
            value["simulated"] = True
            put(cloud, "alert", value["alert_id"], DEVICE,
                value["received_at"], value)
        if rows:
            put(cloud, "cursor", "telemetry", DEVICE,
                datetime.now(timezone.utc), {"last_id": rows[-1]["telemetry_id"]})
        return len(rows), len(alerts)

GUIDANCE = {
    "stable": "Pola simulasi relatif stabil pada jendela ini. Lanjutkan pemantauan.",
    "rising_hr": "Detak jantung simulasi meningkat. Periksa aktivitas dan konteks pembacaan.",
    "falling_spo2": "SpO2 simulasi menurun. Periksa pembacaan dan tindak lanjuti sesuai prosedur tim.",
    "rising_temperature": "Suhu simulasi meningkat. Periksa pembacaan dan pantau perubahan berikutnya.",
}

@router.get("/api/devices/{device_id}/progress")
def progress(device_id: str):
    if device_id != DEVICE:
        raise HTTPException(404, "Unknown demo device")
    try:
        with connect() as cloud:
            cloud.execute("set statement_timeout = '10s'")
            records = cloud.execute(
                """select payload from public.jagsi_demo_records
                where source_id=%s and kind='telemetry' and device_id=%s
                order by observed_at desc, (payload->>'telemetry_id')::bigint desc
                limit 60""", (SOURCE, DEVICE)).fetchall()
            rows = [r[0] for r in reversed(records)]
            if len(rows) != 60:
                return {"state": "insufficient_data", "count": len(rows),
                        "required": 60, "simulated": True}
            times = [datetime.fromisoformat(r["received_at"].replace("Z", "+00:00"))
                     for r in rows]
            span = (times[-1] - times[0]).total_seconds()
            gaps = [(b-a).total_seconds() for a, b in zip(times, times[1:])]
            age = (datetime.now(timezone.utc)-times[-1]).total_seconds()
            if age > 10 or age < -5:
                return {"state": "stale", "age_seconds": age, "simulated": True}
            if not 100 <= span <= 180 or min(gaps) <= 0 or max(gaps) > 6:
                return {"state": "irregular_sampling", "span_seconds": span,
                        "simulated": True}
            values = [[r["heart_rate"], r["spo2"], r["body_temperature"]]
                      for r in rows]
            if any(any(v is None for v in sample) for sample in values):
                return {"state": "missing_values", "simulated": True}
            artifact = joblib.load(MODEL)
            vector = features(values)
            probabilities = artifact["model"].predict_proba([vector])[0]
            index = int(probabilities.argmax())
            label = str(artifact["model"].classes_[index])
            confidence = float(probabilities[index])
            state = "ready" if confidence >= .65 else "uncertain"
            result = {
                "state": state, "label": label, "confidence": confidence,
                "model_version": artifact["version"], "simulated": True,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "from": times[0].isoformat(), "to": times[-1].isoformat(),
                "sample_count": 60, "span_seconds": span,
                "guidance": GUIDANCE[label] if state == "ready" else
                    "Pola belum pasti. Periksa data dan lanjutkan pemantauan.",
                "stats": {"first_10_mean": [sum(r[c] for r in values[:10])/10
                                              for c in range(3)],
                          "last_10_mean": [sum(r[c] for r in values[-10:])/10
                                             for c in range(3)]}}
            identity = f"{rows[-1]['telemetry_id']}-{artifact['version']}"
            put(cloud, "analysis", identity, DEVICE, times[-1], result)
            return result
    except HTTPException:
        raise
    except Exception:
        log.exception("Cloud progress unavailable")
        raise HTTPException(503, "Cloud data or trend model unavailable")

@router.get("/api/devices/{device_id}/cloud-history")
def cloud_history(device_id: str):
    if device_id != DEVICE:
        raise HTTPException(404, "Unknown demo device")
    try:
        with connect() as cloud:
            cloud.execute("set statement_timeout = '10s'")
            rows = cloud.execute(
                """select payload from public.jagsi_demo_records
                where source_id=%s and device_id=%s and kind='telemetry'
                order by observed_at desc, (payload->>'telemetry_id')::bigint desc
                limit 120""", (SOURCE, DEVICE)).fetchall()
            return {"simulated": True, "points": [row[0] for row in reversed(rows)]}
    except Exception:
        log.exception("Cloud history unavailable")
        raise HTTPException(503, "Cloud history unavailable")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            count, alerts = mirror_once()
            log.info("Mirrored telemetry=%s alert_snapshots=%s", count, alerts)
            time.sleep(.1 if count == 200 else 2)
        except KeyboardInterrupt:
            break
        except Exception:
            log.exception("Sync failed; retained local rows will retry")
            time.sleep(5)
```

This reference scopes storage to the one synthetic demo device and mirrors all its alert snapshots to capture acknowledgment changes. Evaluate an incremental alert-update cursor before scaling to many devices. Retain the local database until cloud recovery completes. A new local database requires a new source UUID. Use a UUID saved per checkout, never a fresh UUID on every process start.

### Register and run the extension

1. In `backend/app/main.py`, add the import below after the existing imports. Add `app.include_router(cloud_router)` after the existing `app = FastAPI(...)` statement. Keep the existing endpoints and lifespan.
2. Terminal A must load `.env.demo` before `app.config` constructs settings. Run the wrapper below from `backend`, replacing the original uvicorn command.
3. Open terminal B in `backend`, then start the worker with `..\.venv\Scripts\python.exe -m demo.cloud`.
4. With Wokwi running, wait for the worker to log mirrored telemetry. Open Supabase Table Editor and inspect `jagsi_demo_records`.
5. Wait for 60 regular readings, about two minutes, and request `/api/devices/jagsi-watch-01/progress`. A missing model or cloud failure returns HTTP 503. Insufficient data returns a labelled state.

```python
# app/main.py additions
from demo.cloud import router as cloud_router
# Place this after app = FastAPI(...)
app.include_router(cloud_router)
```

```powershell
..\.venv\Scripts\python.exe -c "from dotenv import load_dotenv; load_dotenv('.env.demo'); import uvicorn; uvicorn.run('app.main:app', host='127.0.0.1', port=8000)"
```

### Cloud verification queries

Run these in Supabase SQL Editor. Filter by your source UUID when multiple team members share the project.

```sql
select source_id, kind, count(*)
from public.jagsi_demo_records group by source_id, kind;

select device_id, observed_at, payload->>'heart_rate' as hr,
       payload->>'spo2' as spo2
from public.jagsi_demo_records where kind='telemetry'
order by observed_at desc limit 10;

select record_id, payload->>'label' as label,
       payload->>'model_version' as model,
       payload->>'guidance' as guidance
from public.jagsi_demo_records where kind='analysis'
order by observed_at desc limit 10;
```

Stop and restart the mirror, then run the first query again while Wokwi is stopped. Counts must remain stable. Pause internet for a minute with SQLite still collecting if the broker route allows it, or block only database access for the worker. Restore access and verify the cursor catches up. MQTT and cloud failure are different failure modes and need separate evidence.

## 12 Connect the dashboard

Owner Akmal · Complexity L3

1. Create `frontend/.env.local` with the values below. Restart Next.js whenever those values change.
2. Preserve `frontend/lib/api.ts`, `useLiveVitals.ts` and `LiveVitals.tsx` for the existing live view. Mark every Wokwi reading as simulated, including DS18B20. The previous temperature badge distinguished simulated HR from a temperature measured inside Wokwi. For this demonstration all observations are virtual.
3. Add `ProgressPanel.tsx` below and place `<ProgressPanel />` on Beranda or Monitoring. Add its import from the actual relative path. The API module uses `NEXT_PUBLIC_JAGSI_API` and `NEXT_PUBLIC_JAGSI_DEVICE_ID`.
4. Connect Riwayat to `/api/devices/{id}/cloud-history`. Map each returned point's `received_at`, `heart_rate`, `spo2` and `body_temperature` to the existing chart shape. Preserve actual timestamp spacing and units.
5. Connect Darurat to existing `fetchAlerts` and the POST acknowledgment endpoint. Display unresolved alerts on every page. Use the existing `/api/stream` alert and alert_ack events initially. If implementing WebSockets in #13, preserve acknowledgment and reconnect semantics and verify allowed Origins.
6. Add the one-time user gesture that enables audio. Muting sound leaves the unresolved alert visible. Acknowledgment marks it handled and updates all open dashboard tabs.
7. Remove the old AI chat input from this demo or replace it with explicit questions such as “Show recent trend” that query the model and stored statistics. Any interactive answer must be traceable to the endpoint. The plan requires no conversational model service.

```dotenv
NEXT_PUBLIC_JAGSI_API=http://127.0.0.1:8000
NEXT_PUBLIC_JAGSI_DEVICE_ID=jagsi-watch-01
```

```tsx
'use client';

import { useEffect, useState } from 'react';
import { API_BASE, DEVICE_ID } from '../lib/api';

type Progress = {
  state: string;
  label?: string;
  confidence?: number;
  model_version?: string;
  guidance?: string;
  from?: string;
  to?: string;
  sample_count?: number;
};

export default function ProgressPanel() {
  const [data, setData] = useState<Progress | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function refresh() {
      try {
        const response = await fetch(
          `${API_BASE}/api/devices/${encodeURIComponent(DEVICE_ID)}/progress`,
          { cache: 'no-store', signal: controller.signal },
        );
        if (!response.ok) throw new Error('Analisis belum tersedia');
        const result = await response.json() as Progress;
        if (!controller.signal.aborted) { setData(result); setError(''); }
      } catch (failure) {
        if (!controller.signal.aborted) {
          setData(null);
          setError(failure instanceof Error ? failure.message : 'Koneksi terputus');
        }
      } finally {
        if (!controller.signal.aborted) timer = setTimeout(refresh, 10000);
      }
    }
    void refresh();
    return () => { controller.abort(); clearTimeout(timer); };
  }, []);
  return (
    <section aria-label="Analisis tren JagSi">
      <h2>Analisis tren JagSi</h2>
      <p>Data simulasi Wokwi</p>
      <div aria-live="polite">
        {error ? <p>{error}</p> : <p>{data?.guidance ?? data?.state ?? 'Memuat analisis'}</p>}
      </div>
      {data?.label && <p>Pola {data.label} · Keyakinan {Math.round((data.confidence ?? 0) * 100)}%</p>}
      {data?.model_version && <p>Model {data.model_version} · {data.sample_count} sampel</p>}
      {data?.from && <p>{new Date(data.from).toLocaleString('id-ID')} hingga {new Date(data.to!).toLocaleString('id-ID')}</p>}
    </section>
  );
}
```

The component handles serial refreshes to avoid overlapping requests and removes a prior result on failure. Apply the existing design system during implementation. Add explicit Indonesian labels for `stale`, `insufficient_data`, `irregular_sampling`, `missing_values` and `uncertain` before acceptance.

Run `npm run dev` from `frontend`, open http://localhost:3000 and verify API traffic in browser Network tools. A backend response alone does not establish that the user sees live data. Confirm that demo fallback cannot silently replace a disconnected sensor feed with normal-looking values.

## 13 Presentation scenarios and observed history

Owner Akmal coordinates · Complexity L3

1. Start backend, mirror and dashboard, then run Wokwi. Show the circuit and Serial Monitor. Open `/api/health` and show connected broker and loaded classifier.
2. Hold the virtual MPU6050 at stillness. Set HR near 75, SpO2 near 98 and virtual temperature near 36.6. Wait for 60 telemetry records. Show the observed time span and predicted stable pattern.
3. Increase HR smoothly across about two minutes, leaving other inputs stable. Show the actual recorded values, predicted pattern, confidence and caregiver guidance. Repeat with falling SpO2 and rising temperature in separate sessions.
4. Run an isolated ML-only fall replay and show the model-sourced alert. Demonstrate the SOS button separately, then acknowledge it on the dashboard.
5. Open Supabase SQL Editor and show telemetry and analysis rows. Restart the application and reload cloud history. The stored history must survive the restart.
6. Stop the simulator. Show stale/disconnected state rather than a current healthy label.
7. If demonstrating several days of health progress, generate an explicitly labelled accelerated scenario with intended observation timestamps in a separate device or source UUID. Add a separate timestamp contract and an aggregation model before acceptance. The reference trend model analyzes approximately two minutes and cannot substantiate a multi-day health-progress claim.

The first presentation milestone covers live two-minute trend analysis. A later milestone can add daily aggregate features and a separately evaluated longitudinal model. The team must agree on that scope before describing its output as daily health progress.

## 14 Integration tests and definition of done

| Check | Expected result | Owner |
| --- | --- | --- |
| Pinned baseline test suites | Backend and frontend pass, firmware buffer test passes on C++17 toolchain | Akhnaf and Akmal |
| Wokwi start and controls | Potentiometers and virtual temperature change actual incoming values | Akhnaf |
| Motion window contract | 30 finite chronological samples, 10 Hz, correctly represented gaps | Akhnaf |
| ML-only replay | At least one alert explicitly sourced from the classifier | Akhnaf |
| False-positive evaluation | Held-out synthetic metrics and activity counts saved | Akhnaf |
| Trend holdout | Macro-F1 and per-class confusion matrix published with synthetic provenance | Akhnaf |
| Missing and stale input | No ready prediction on incomplete, old or irregular input | Rafi |
| Five SOS presses | Unique events, durable receipt acknowledgment, caregiver handling separate | All |
| Cloud retry | Interrupted batches replay safely and cursor advances after commit | Rafi |
| Restart and cloud history | History persists, source ID remains stable | Rafi |
| Frontend failure states | Disconnection and model/cloud errors are visible | Akmal |
| Two dashboards | Acknowledgment is reflected in both; opt-in alarm is verified | Akmal |
| Secrets | DSN absent from commits, Wokwi project and frontend bundle | Rafi |
| Final delivery | Model hashes, Wokwi URL, commit, dependencies and demo evidence linked | All |

Run new regression tests against the specific defects they protect. Include NaN and Infinity rejection, sensor-gap aging, telemetry cursor rollback, repeated upsert, alert status change, a source-ID collision, stale prediction, irregular timing, missing model and unavailable cloud. Compile the firmware in Wokwi. Run the frontend lint, TypeScript, tests and production build after adding the component.

Create `docs/evidence/wokwi-owned-ai/` for sanitized logs and screenshots. Record the source commit, model hashes, test commands, observed latency and date in a short validation record. Store no real credentials or person-linked health data. Close each assigned issue only after its listed evidence is attached.

## 15 Troubleshooting and operating limits

| Symptom | Check and recovery |
| --- | --- |
| Wokwi publishes but backend stays empty | Match broker, topic prefix and device ID in all processes. A laptop localhost URL is not reachable through Wokwi's public gateway. |
| Every motion window is rejected | Compare units, sample count and dropped-sample counter. Check blocking temperature reads and reconnect gaps. |
| Falls appear during walking | Review threshold and session evaluation. Save the failure and tune on a separate split. |
| Replays show device-rule alerts only | Stop Wokwi, suppress fake device rule events, clear recent cooldown state by waiting, and inspect alert source. |
| Cloud connection fails | Check copied pooler username, region, URL-encoded password, SSL mode and project pause status. |
| Mirror log repeats failures | Keep SQLite intact, inspect SQL grants and network, fix access and restart with the same UUID. |
| Progress waits indefinitely | Need 60 regular readings. Verify two-second cadence, cloud cursor and virtual DS18B20 values. |
| A model result appears after the data stop | Ensure endpoint freshness checks and UI error state remain enabled. |
| UI still uses mock values | Verify actual component imports, API base and environment restart. |
| Sound is silent | Use the user gesture to allow audio and test a real browser output device. |

Supabase Free currently includes 500 MB database space and pauses after one week of inactivity. Run a one-hour demo, measure table sizes with `pg_total_relation_size`, and calculate retention from that measurement. Keep the mirror target to demo telemetry and analysis, with a chosen retention policy before long-running use. Watch storage rather than assuming a permanent unlimited free deployment.

## 16 Issue alignment

| Issue | State for this plan | Accountable person | Treatment |
| --- | --- | --- | --- |
| #20 | Open | Akhnaf | Wokwi and both model implementations |
| #21 | Open | Rafi | Supabase and inference backend |
| #22 | Open | Akmal | UI integration and acceptance |
| #5 | Open | Akhnaf | Wokwi simulation scope, physical replacement tracked separately |
| #9 | Open | Akhnaf | Fall performance and physical validation retain their evidence requirements |
| #10 | Open, scope revised | Rafi | Owned model progress and caregiver guidance replace external model API |
| #13 | Open | Akmal | Notification acceptance remains required |
| #8 | Open, deferred for selected demo | Rafi | Azure integration remains documented for future scope |
| #7 | Open, deferred for selected demo | Akhnaf | Physical casing remains a future hardware task |
| #6, #11, #12, #14, #19 | Closed | Existing ownership retained | Existing completed work and calibration protocol |

## 17 Sources and code locations

- Project README and team membership, inspected 18 November 2026. https://github.com/akhnafyooga/JagSi/blob/a5c755007f16b8d24d0ba47037c86856a6476678/README.md
- Reproducible code baseline and complete firmware files. https://github.com/akhnafyooga/JagSi/tree/b6278df5fbc6444be805a0cb0970a5b24665981f/firmware/jagsi-watch
- Existing API, store, bridge and configuration. https://github.com/akhnafyooga/JagSi/tree/b6278df5fbc6444be805a0cb0970a5b24665981f/backend/app
- Published synthetic fall validation. https://github.com/akhnafyooga/JagSi/blob/b6278df5fbc6444be805a0cb0970a5b24665981f/docs/week6-validation.md
- Wokwi virtual Wi-Fi and public gateway. https://docs.wokwi.com/guides/esp32-wifi
- Wokwi MPU6050 reference. https://docs.wokwi.com/parts/wokwi-mpu6050
- Wokwi potentiometer reference. https://docs.wokwi.com/parts/wokwi-potentiometer
- Wokwi DS18B20 reference. https://docs.wokwi.com/parts/wokwi-ds18b20
- Supabase database connection and pooler setup. https://supabase.com/docs/guides/database/connecting-to-postgres
- Supabase row level security. https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase Free limits. https://supabase.com/pricing

### Reference code verification on 18 November 2026

The four Python blocks were parsed successfully. The trend-training example was executed in temporary storage and reported macro-F1 1.0 on 150 held-out synthetic sessions generated by the same scenario generator. This is a code smoke test. Independent generators, mixed scenarios and physical data need separate evaluation. Cloud credentials were unavailable for this document task, so live Supabase synchronization, firmware compilation and the updated dashboard were not exercised. Their acceptance checks remain assigned to #20, #21 and #22.

Reference snippets must be implemented on the shared integration branch and verified against these contracts. Record future departures in the document and linked issues so the three workstreams stay aligned.
