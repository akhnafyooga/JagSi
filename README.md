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

## Target System Architecture

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
                       │ WebSocket / API
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

## Planned Product Features

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
| Real-time Communication | WebSockets              |
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

The [sprint status](docs/index.md#sprint-status) tracks delivery against the original six workstreams.

## Run the development baseline

The documented end-to-end development setup lives on the [Week 6 integration branch](https://github.com/akhnafyooga/JagSi/tree/b6278df5fbc6444be805a0cb0970a5b24665981f). Follow its [firmware setup](https://github.com/akhnafyooga/JagSi/blob/b6278df5fbc6444be805a0cb0970a5b24665981f/firmware/README.md) and [backend and dashboard setup](https://github.com/akhnafyooga/JagSi/blob/b6278df5fbc6444be805a0cb0970a5b24665981f/backend/README.md) for the MQTT development environment.

## Project Status

**17 November 2026**

| Workstream | Current evidence |
| --- | --- |
| Wearable and MQTT | Wokwi firmware publishes telemetry, alerts, and device state and receives commands. Heart rate and SpO2 are simulated in Wokwi. Physical sensor and casing validation remain open. |
| Week 6 integration | PR #18 contains the 30-sample, 10 Hz motion windows, FastAPI MQTT bridge, SQLite storage, and live dashboard feed over server-sent events. The pull request is open. |
| Fall detection | The original model scored 0.985 recall and 0.914 precision on held-out synthetic windows from its training generator. Firmware-shaped synthetic validation yielded 0.403 precision and flagged 96.5% of walking windows at threshold 0.11. Physical MPU6050 calibration and held-out evaluation remain open. |
| Azure and Gemini | Week 7 reports local Event Grid replay, threshold-retuning tooling, and Bahasa Indonesia summaries and chat with a rule-based fallback. A published Week 7 commit, live Azure and Gemini checks, and an ESP32 target build are pending. |

See the [project portal](docs/index.md) for sprint status, issue links, and validation evidence.
