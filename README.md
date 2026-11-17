# JagSi — Jaga Lansia

> **Cloud-connected wearable health monitoring and caregiver companion system for elderly individuals.**

JagSi (**Jaga Lansia**) is a wearable health-monitoring ecosystem designed to help elderly individuals stay safer while allowing family caregivers to remotely monitor their condition.

The system combines **embedded hardware, cloud telemetry, machine learning, and an accessible web dashboard** to provide real-time vital sign monitoring, automatic fall detection, emergency SOS alerts, and AI-generated health summaries.

---

## Team

| Role             | Name                     | Student ID |
| ---------------- | ------------------------ | ---------- |
| **Group Leader** | Rafi Busthami            | 532760     |
| **Member**       | Akhnaf Fawzan Yogatrisna | 536720     |
| **Member**       | Akmal Rafli Fauzan       | 533033     |

---

## Product Goals

JagSi aims to build an accessible and cloud-connected wearable system that provides:

* Real-time heart-rate monitoring
* SpO₂ monitoring
* Body-temperature monitoring
* Automatic fall detection
* Physical emergency SOS activation
* Emergency alerts for caregivers
* Real-time health telemetry dashboard
* AI-driven health risk summaries
* Historical health data for monitoring and evaluation

The system is designed around the needs of elderly individuals and their caregivers, with an emphasis on simplicity, accessibility, and rapid emergency notification.

---

## System Architecture

```text
┌──────────────────────────────────────────────────────────────┐
│                         JAGSI SYSTEM                         │
└──────────────────────────────────────────────────────────────┘

        ┌─────────────────────────────┐
        │      1. WEARABLE DEVICE     │
        │                             │
        │  ESP32                      │
        │   ├── MAX30102              │
        │   │    ├─ Heart Rate        │
        │   │    └─ SpO₂              │
        │   │                         │
        │   ├── MPU6050               │
        │   │    └─ Motion / Fall     │
        │   │                         │
        │   ├── Temperature Sensor    │
        │   └── Physical SOS Button   │
        └──────────────┬──────────────┘
                       │
                       │ MQTT
                       ▼
        ┌─────────────────────────────┐
        │       2. CLOUD + AI         │
        │                             │
        │  Azure IoT Hub              │
        │        ↓                    │
        │  Event Grid / Telemetry     │
        │        ↓                    │
        │  FastAPI Backend            │
        │        ↓                    │
        │  ┌───────────────────────┐  │
        │  │ Fall Detection ML     │  │
        │  │ Gemini AI             │  │
        │  └───────────────────────┘  │
        └──────────────┬──────────────┘
                       │
                       │ WebSocket (alerts) / SSE (telemetry) / REST
                       ▼
        ┌─────────────────────────────┐
        │   3. CAREGIVER DASHBOARD    │
        │                             │
        │        Next.js Web App      │
        │                             │
        │  ├── Live Vital Signs       │
        │  ├── Emergency Alerts       │
        │  ├── Historical Charts      │
        │  ├── Alert Logs             │
        │  └── AI Health Summary      │
        └─────────────────────────────┘
```

---

## Core Features

### 1. Embedded Hardware and Telemetry

The wearable device uses an **ESP32** as its primary microcontroller and interfaces with health and motion sensors.

Hardware components:

* ESP32
* MAX30102
* MPU6050
* Temperature sensor
* Physical emergency SOS button

The wearable continuously collects health and motion data and streams telemetry to the cloud through MQTT. The planned sensor sampling rate is **10 Hz** for continuous tracking.

Collected data includes:

```text
Heart Rate
SpO₂
Body Temperature
Motion Vectors
```

### 2. Emergency Detection

JagSi supports two primary emergency mechanisms.

#### Automatic Fall Detection

Motion data from the MPU6050 is processed to identify potential falls using a machine-learning classification model.

The model uses motion characteristics such as:

* Accelerometer spikes
* Pitch
* Roll
* Impact-related movement

When a potential fall is detected, the system can trigger an emergency notification to the caregiver.

#### Manual SOS

The wearable includes a physical **SOS button** that allows the elderly user to manually trigger an emergency alert.

### 3. Cloud Infrastructure

JagSi uses cloud infrastructure to receive and process wearable telemetry.

```text
ESP32
  │
  │ MQTT
  ▼
Azure IoT Hub
  │
  ▼
Event Grid
  │
  ▼
Backend Services
  │
  ├── Fall Detection
  ├── Health Data Processing
  └── AI Health Summary
```

The cloud layer provides the ingestion endpoint for wearable telemetry and uses secure MQTT authentication through device certificates.

### 4. AI Health Assistant

JagSi integrates **Gemini API** and a **FastAPI backend** to transform raw health telemetry into easier-to-understand health summaries.

The AI component is intended to provide:

* Natural-language health summaries
* Health risk information
* Bahasa Indonesia summaries
* AI-assisted caregiver information

This allows caregivers to understand health telemetry without having to interpret raw sensor values themselves.

### 5. Caregiver Dashboard

The caregiver-facing application is developed using **Next.js**.

The dashboard provides:

* Real-time vital-sign gauges
* Historical health charts
* Emergency alert notifications
* Alert logs
* AI-generated health summaries

The interface prioritizes accessibility and high-contrast visual design for family caregivers.

---

## Target Users

### Elderly Individuals

The wearable is designed to be:

* Simple to operate
* Non-intrusive
* Easy to understand
* Equipped with a physical SOS button
* Usable with minimal technical knowledge

### Family Caregivers and Adult Children

Caregivers can use the web dashboard to:

* Monitor vital signs
* Receive emergency alerts
* Review health trends
* Understand AI-generated health summaries

### Healthcare Providers

The system can provide historical health telemetry that may be exported for evaluation, including:

* Heart rate
* SpO₂
* Body temperature
* Fall frequency

These user groups and their needs are defined in the project's SDLC design.

---

## Functional Requirements

| ID      | Requirement                                                                                                                                                      |
| ------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **FR1** | The system shall collect and monitor heart rate, SpO₂, and body temperature from the wearable and stream the data to the cloud.                                  |
| **FR2** | The system shall detect emergency events, including automatic fall detection and manual SOS activation, and send emergency alerts to caregivers.                 |
| **FR3** | The system shall provide caregivers with a web dashboard containing real-time telemetry, emergency alerts, and AI-generated health risk summaries in Indonesian. |

---

## Technology Stack

| Layer                   | Technology              |
| ----------------------- | ----------------------- |
| Microcontroller         | ESP32                   |
| Health Sensor           | MAX30102                |
| Motion Sensor           | MPU6050                 |
| Communication           | MQTT                    |
| Cloud Platform          | Microsoft Azure         |
| IoT Infrastructure      | Azure IoT Hub           |
| Cloud Events            | Azure Event Grid        |
| Backend                 | FastAPI                 |
| Machine Learning        | Fall Detection ML Model |
| AI                      | Gemini API              |
| Frontend                | Next.js                 |
| Real-time Communication | WebSocket for emergency alerts, Server-Sent Events for telemetry |
| UI Design               | Figma                   |

The technology choices correspond to the architecture and project breakdown defined in the project worksheet.

---

## Development Methodology

JagSi follows **Agile development using the Scrum framework**, with **2-week sprint cycles**.

Agile was selected because JagSi requires simultaneous development and integration of:

* Embedded hardware
* Cloud infrastructure
* Backend services
* Machine learning
* Frontend interfaces

The methodology also supports iterative caregiver and user feedback and rapid testing of complex components such as fall-detection models.

---

## Development Roadmap

The project is planned across six sprints:

| Sprint       | Focus                                                  |
| ------------ | ------------------------------------------------------ |
| **Sprint 1** | Brainstorming and SDLC Planning                        |
| **Sprint 2** | Low-Fidelity Wireframing and Wokwi Hardware Simulation |
| **Sprint 3** | Azure IoT Hub and MQTT Ingestion                       |
| **Sprint 4** | ML Model and Gemini AI Backend                         |
| **Sprint 5** | Caregiver Web Application                              |
| **Sprint 6** | End-to-End Testing, CI/CD and Final Documentation      |

Each sprint represents two project sessions according to the project Gantt chart.

---

## Project Structure

```text
JagSi/
├── firmware/                 ESP32 watch (Arduino C++)
│   ├── jagsi-watch/          sketch.ino, Wokwi diagram.json, Azure transport
│   └── test/                 host tests and a type-check of the sketch
├── backend/                  FastAPI service, see backend/README.md
│   ├── app/                  MQTT / Event Grid bridge, API, SSE, alert WebSocket,
│   │                         Gemini summary, SQLite store
│   ├── ml/                   fall classification model and re-tuning
│   └── scripts/              dev broker and end-to-end checks
├── frontend/                 Next.js caregiver dashboard (Bahasa Indonesia)
│   ├── app/                  pages: Beranda, Monitoring, Riwayat, Profil, Darurat
│   ├── components/           UI, including the emergency alert screen
│   └── lib/                  API client, live data hooks, alarm
├── infra/azure/deploy.sh     creates the IoT Hub, device and Event Grid subscription
├── tools/                    fake device and MQTT monitor for testing without hardware
├── tests/                    payload schema and pipeline tests for the firmware contract
├── docs/                     GitHub Pages site, MQTT contract, Azure setup,
│                             hardware BOM, weekly validation results
└── .github/workflows/        CI
```

---

## Getting Started

You need Python 3.12, Node.js 20 and, for the device, either [Wokwi](https://wokwi.com)
or the fake device in `tools/`. Azure and a Gemini key are optional for local work.

### 1. Local MQTT broker

```bash
cd backend
pip install -r requirements-dev.txt amqtt
python3 scripts/dev_broker.py --port 1883
```

### 2. Backend

```bash
cd backend
JAGSI_MQTT_HOST=127.0.0.1 uvicorn app.main:app --reload --port 8000
```

Optional: `GEMINI_API_KEY=...` for AI summaries (without it, a rule-based summary is
shown and labelled as such). All settings are listed in `backend/README.md`.

### 3. Dashboard

```bash
cd frontend
cp .env.local.example .env.local      # NEXT_PUBLIC_JAGSI_API=http://localhost:8000
npm ci
npm run dev                           # http://localhost:3000
```

On the first visit, press **Aktifkan alarm darurat** once. Browsers only allow sound
and notifications after a click.

### 4. A device

Either load `firmware/jagsi-watch` in Wokwi (see `firmware/README.md`), or:

```bash
python3 tools/fake_device.py --host 127.0.0.1 --device-id jagsi-watch-01 --fall-at 5
```

A few seconds later the dashboard shows the emergency screen and rings until someone
presses **Saya tangani**.

### Azure IoT Hub

Run `infra/azure/deploy.sh` and follow `docs/azure-setup.md`; then start the backend
with `JAGSI_INGEST=azure`.

---

## Real-time Notifications

Emergencies reach the caregiver without polling:

```text
watch --MQTT/IoT Hub--> backend --stores alert--> WS /ws/alerts --> every open dashboard
                                                       │                 │
watch <--ack_alert------ backend <--"Saya tangani"-----┘   full-screen alert, alarm,
                                                           system notification
```

- A fall or SOS opens a full-screen alert on whatever page is open, with an alarm
  tone and, if the tab is in the background, a system notification.
- The alert stays until a caregiver presses **Saya tangani**; muting only stops the
  sound. The acknowledgement closes it on every other open dashboard and stops the
  watch from re-sending.
- A dashboard that reconnects receives every alert nobody has handled yet.
- Telemetry keeps using Server-Sent Events (`/api/stream`), which only needs one
  direction.

---

## CI/CD

GitHub Actions (`.github/workflows/main.yml`) runs on every push to `main` and
`feat/**` and on every pull request:

| Job | What it runs |
|-----|--------------|
| Frontend | `npm ci`, lint, type check, Vitest, production build (Node.js 20) |
| Backend | pytest, the MQTT pipeline check, the Event Grid check, the real-time alert check, and a non-blocking model validation (Python 3.12) |
| Firmware | motion-window and direct-method tests in C++, and a type-check of `sketch.ino` for both transports |

---

## Project Documentation

The project documentation includes:

* Product goals
* User requirements
* Use Case Diagram
* Entity Relationship Diagram
* Low-Fidelity Wireframe
* Functional Requirements
* System Architecture
* Project Breakdown
* Gantt Chart
* GitHub Project Management
* GitHub Actions CI/CD

---

## Project Status

**Development Status:** In Development (Week 8)

| Sprint | Focus | Status |
|--------|-------|--------|
| Sprint 1 | Brainstorming and SDLC Planning | Done |
| Sprint 2 | Low-Fidelity Wireframing and Wokwi Hardware Simulation | Done |
| Sprint 3 | Azure IoT Hub and MQTT Ingestion | MQTT done; Azure code done, deployment pending |
| Sprint 4 | ML Model and Gemini AI Backend | Gemini done; model threshold waits for real sensor recordings |
| Sprint 5 | Caregiver Web Application | In progress: live vitals, AI summary, emergency alerts done |
| Sprint 6 | End-to-End Testing, CI/CD and Final Documentation | CI in place |

Progress per week is documented in `docs/week6-validation.md`,
`docs/week7-validation.md` and `docs/week8-validation.md`.
