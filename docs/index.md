# JagSi (Jaga Lansia) — Senior Project Documentation

## Product Goals
To build an accessible, cloud-connected wearable health-monitoring ecosystem that provides real-time vital sign tracking, automated fall detection, emergency alerts, and AI-driven health risk summaries for elderly individuals and their primary caregivers.

## Potential Users and Needs
* **Elderly Individuals:** Require simple, non-intrusive wearable hardware equipped with vital sensors and an accessible physical SOS button with zero UI learning curve.
* **Family Caregivers:** Require a web dashboard offering live health metrics, instant push notifications for fall events, and simplified AI explanations of telemetry.
* **Healthcare Providers:** Require organized historical health trends (heart rate, SpO2, temperature) to evaluate overall patient conditions.

---

## Functional Requirements
| FR | Description |
| :--- | :--- |
| **FR 1** | The simulated ESP32 wearable must collect and stream heart rate, SpO2, and body temperature telemetry to Azure IoT Hub via MQTT every 10 seconds. |
| **FR 2** | The cloud backend must process accelerometer/gyroscope vectors using an ML model to detect fall impacts and dispatch emergency alerts within 5 seconds. |
| **FR 3** | The system must allow users to trigger a manual emergency SOS alert by holding the wearable's physical button for >2 seconds. |
| **FR 4** | The web dashboard must integrate the Gemini API to analyze raw telemetry and deliver simplified health risk summaries in Bahasa Indonesia. |

---

## Entity Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS ||--o{ DEVICES : owns
    DEVICES ||--o{ TELEMETRY_LOGS : generates
    DEVICES ||--o{ ALERTS : triggers

    USERS {
        string user_id PK
        string name
        string role
        string phone_number
        datetime created_at
    }

    DEVICES {
        string device_id PK
        string user_id FK
        string mac_address
        string status
        datetime last_active
    }

    TELEMETRY_LOGS {
        string log_id PK
        string device_id FK
        int heart_rate
        int spo2
        float temperature
        datetime timestamp
    }

    ALERTS {
        string alert_id PK
        string device_id FK
        string alert_type
        string status
        datetime timestamp
    }
```

---

## Gantt-Chart Sprint Based
```mermaid
gantt
    title JagSi Development Timeline (6 Sprints / 12 Sessions)
    dateFormat  YYYY-MM-DD
    axisFormat  Sprint %W

    section Sprint 1
    SDLC Planning & Architecture          :done, s1, 2026-09-01, 2026-09-14
    section Sprint 2
    Wokwi Hardware Sim & Figma UI         :active, s2, 2026-09-15, 2026-09-28
    section Sprint 3
    Azure IoT Hub & MQTT Ingestion        :s3, 2026-09-29, 2026-10-12
    section Sprint 4
    ML Model & Gemini AI Backend          :s4, 2026-10-13, 2026-10-26
    section Sprint 5
    Caregiver Web App Development         :s5, 2026-10-27, 2026-11-09
    section Sprint 6
    E2E Testing, CI/CD & Final Docs       :s6, 2026-11-10, 2026-11-23
```

## UI/UX Design & Low-Fidelity Wireframes

Below is the initial low-fidelity component breakdown for the JagSi Caregiver Web App:

* **Header:** Navigation, real-time alerts, user profile.
* **Alert Banner:** Prominent notification strip for critical fall events (UC-02 / UC-03).
* **Telemetry Grid:** Live monitoring cards for Heart Rate, SpO2, Body Temp, and Battery status.
* **AI Health Digest:** Section summarizing daily vital trends via Gemini API (Bahasa Indonesia).
* **AI Chat Assistant:** Interactive prompt area for caregiver health queries.

![JagSi Lo-Fi Wireframe](../assets/jagsi_dashboard.svg)