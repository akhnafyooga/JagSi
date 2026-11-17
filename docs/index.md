# JagSi (Jaga Lansia) — Senior Project Documentation

**Live Documentation Portal**: [https://akhnafyooga.github.io/JagSi/](https://akhnafyooga.github.io/JagSi/)

---

## Product Goals
To build an accessible, cloud-connected wearable health-monitoring ecosystem that provides real-time vital sign tracking, automated fall detection, emergency alerts, and AI-driven health risk summaries for elderly individuals and their primary caregivers.

---

## Potential Users and Needs
* **Elderly Individuals**: Require simple, non-intrusive wearable hardware equipped with vital sensors and an accessible physical SOS button with zero UI learning curve.
* **Family Caregivers**: Require a web dashboard offering live health metrics, instant push notifications for fall events, and simplified AI explanations of telemetry.
* **Healthcare Providers**: Require organized historical health trends (heart rate, SpO2, temperature) to evaluate overall patient conditions.

---

## Functional Requirements

| FR | Description |
| :--- | :--- |
| **FR 1** | The simulated ESP32 wearable must collect and stream heart rate, SpO2, and body temperature telemetry to Azure IoT Hub via MQTT every 10 seconds. |
| **FR 2** | The cloud backend must process accelerometer/gyroscope vectors using an ML model to detect fall impacts and dispatch emergency alerts within 5 seconds. |
| **FR 3** | The system must allow users to trigger a manual emergency SOS alert by holding the wearable’s physical button for >2 seconds. |
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
## Sprint Status

**17 November 2026**

| Sprint | Status | Progress and remaining work |
| --- | --- | --- |
| 1. Planning and documentation | Complete | Product scope, functional requirements, ERD and the Pages portal are in place ([#14](https://github.com/akhnafyooga/JagSi/issues/14)). |
| 2. Hardware simulation and UI design | In progress | MQTT pub/sub was validated with Wokwi and a public broker ([#6](https://github.com/akhnafyooga/JagSi/issues/6), [PR #17](https://github.com/akhnafyooga/JagSi/pull/17)). The Week 6 branch records the physical and simulated sensor configurations ([#5](https://github.com/akhnafyooga/JagSi/issues/5)). Wireframes and the dashboard exist. Final design-kit evidence and physical assembly remain open ([#11](https://github.com/akhnafyooga/JagSi/issues/11), [#7](https://github.com/akhnafyooga/JagSi/issues/7)). |
| 3. Cloud ingestion | In progress | The [Week 6 PR](https://github.com/akhnafyooga/JagSi/pull/18) provides a development MQTT-to-SQLite bridge and API. Week 7 reports 17/17 local Event Grid replay checks. Publish the tested revision and validate X.509 device traffic and direct-method acknowledgments on Azure ([#8](https://github.com/akhnafyooga/JagSi/issues/8)). |
| 4. Fall detection and caregiver AI | In progress | The reproducible classifier and device-format validation are available. Week 7 reports synthetic calibration tooling and summary and chat with a labelled rule-based fallback. Physical MPU6050 recordings, held-out model evaluation and live Gemini requests remain open ([#9](https://github.com/akhnafyooga/JagSi/issues/9), [#10](https://github.com/akhnafyooga/JagSi/issues/10)). |
| 5. Caregiver dashboard | In progress | The Next.js screens are implemented on the frontend branch ([#12](https://github.com/akhnafyooga/JagSi/issues/12)). PR #18 demonstrates SSE vitals with polling and demo fallback. Verify audible emergency notifications and agree on the transport acceptance criterion ([#13](https://github.com/akhnafyooga/JagSi/issues/13)). |
| 6. System validation and release | In progress | Week 6 reports 22 local end-to-end bridge checks and 22 frontend tests. Week 7 reports 103 backend and 31 frontend tests pending a published commit and CI run. Physical hardware, live services and a CI run that enforces backend test failures remain pending. |

### Sprint issue diagram

![JagSi sprint issue status by workstream. Seven issues are open and three are closed.](assets/sprint-issue-status.svg)

This snapshot shows GitHub issue states as of 17 November 2026. Sprint 6 validation is tracked across the existing hardware, cloud, model, AI and notification issues.

- **Open:** [#5 Wokwi sensors](https://github.com/akhnafyooga/JagSi/issues/5), [#7 wearable assembly](https://github.com/akhnafyooga/JagSi/issues/7), [#8 Azure ingestion](https://github.com/akhnafyooga/JagSi/issues/8), [#9 fall model](https://github.com/akhnafyooga/JagSi/issues/9), [#10 AI health digests](https://github.com/akhnafyooga/JagSi/issues/10), [#11 wireframes and component kit](https://github.com/akhnafyooga/JagSi/issues/11), and [#13 emergency notifications](https://github.com/akhnafyooga/JagSi/issues/13).
- **Closed:** [#6 MQTT pipeline](https://github.com/akhnafyooga/JagSi/issues/6), [#12 Next.js frontend](https://github.com/akhnafyooga/JagSi/issues/12), and [#14 initial documentation](https://github.com/akhnafyooga/JagSi/issues/14).

### Published development evidence

- [MQTT contract](https://github.com/akhnafyooga/JagSi/blob/b6278df5fbc6444be805a0cb0970a5b24665981f/docs/mqtt-contract.md) and [hardware bill of materials](https://github.com/akhnafyooga/JagSi/blob/b6278df5fbc6444be805a0cb0970a5b24665981f/docs/hardware-bom.md).
- [Week 6 validation](https://github.com/akhnafyooga/JagSi/blob/b6278df5fbc6444be805a0cb0970a5b24665981f/docs/week6-validation.md) and [live dashboard capture](https://github.com/akhnafyooga/JagSi/blob/b6278df5fbc6444be805a0cb0970a5b24665981f/docs/evidence/dashboard-live.png).
- [Week 6 CI run](https://github.com/akhnafyooga/JagSi/actions/runs/41872493421) and [workflow configuration](https://github.com/akhnafyooga/JagSi/blob/b6278df5fbc6444be805a0cb0970a5b24665981f/.github/workflows/main.yml). The backend test step allows failures, so the overall green result has limited coverage.

## UI/UX Design & Low-Fidelity Wireframe
UI/UX Design & Low-Fidelity Wireframes
Below is the initial low-fidelity component breakdown for the JagSi Caregiver Web App:

![JagSi dashboard](assets/jagsi_dashboard.svg)

Header: Navigation bar, real-time status/alerts indicator, user profile.

Alert Banner: Prominent notification strip for critical fall events or manual emergency SOS triggers.

Telemetry Grid: Live monitoring cards for Heart Rate, SpO2, Body Temperature, and Battery status.

AI Health Digest: Section summarizing daily vital trends via Gemini API in Bahasa Indonesia.

AI Chat Assistant: Interactive prompt area for caregiver health queries and AI-assisted updates.
