# ABAL - Jaga Lansia (JagSi)

**IT Senior Project**  
Department of Electrical and Information Engineering, Faculty of Engineering, Universitas Gadjah Mada  

---

## Group Information

**Group Name:** ABAL  

**Team Members:**
* **Rafi Busthami** (NIM: 24/532760/TK/58998) – Group Leader / Cloud Engineer (CE)
* **Akmal Rafli Fauzan** (NIM: 24/533033/TK/59053) – UI-UX Designer / Project Manager
* **Akhnaf Fawzan Yogatrisna** (NIM: 24/536720/TK/59561) – Software Engineer / AI Engineer

---

## Module 1: Product Definition & Problem Formulation

### 1. Product Identification
* **Product Name:** Jaga Lansia (JagSi)
* **Product Type:** Wearable Health-Monitoring Watch Prototype & Caregiver Companion Web Dashboard

### 2. Background & Problem Formulation
* **Background:** Indonesia has a rapidly growing elderly population, reaching ~31.4 million in 2023 and projected to exceed 48 million by 2035. Many elderly individuals live alone or far from their adult children. Current healthcare infrastructure lacks continuous remote monitoring, and full-time human caregiving is financially unfeasible for most families.
* **Problem Statement:** How can we enable real-time health monitoring for elderly individuals who live alone or far from family, so that health concerns or emergencies (such as falls) are detected and responded to quickly without requiring frequent clinic visits?

### 3. Proposed Solution & Key Features
* **Proposed Solution:** JagSi is an ESP32-based wearable watch prototype equipped with vital sign sensors and fall detection. It transmits telemetry data via Wi-Fi/MQTT to Azure cloud infrastructure. Machine learning models analyze vital signs and movement patterns, triggering emergency alerts to a companion web dashboard. The system integrates a Gemini-powered Bahasa Indonesia chatbot to deliver accessible health summaries.
* **Key Feature Specifications:**
  * **Wearable Watch & Web Dashboard:** Non-timekeeping sensor watch paired with an accessible family caregiver web portal.
  * **Vital Sign Monitor:** Real-time metrics for heart rate, SpO2, and body temperature.
  * **Fall Detection System:** Accelerometer and gyroscope data processing via ML models to classify impacts and send automated SOS alerts.
  * **AI Health-Risk Analysis:** Combines sensor metrics, medical history, and external API data to evaluate overall health risk status.
  * **Bahasa Indonesia Health Chatbot:** Gemini-driven conversational interface translating complex telemetry into clear explanations.

### 4. Competitor Analysis

| Competitor | Type & Focus | Key Strengths | Key Weaknesses | JagSi Advantage |
| :--- | :--- | :--- | :--- | :--- |
| **Whoop** | Direct (Fitness / Recovery) | 24/7 continuous tracking, advanced physiological recovery metrics | High subscription fee (~$30/mo); lacks fall detection, SOS, or Bahasa Indonesia support | Low-cost hardware targeting elderly health, automated fall alerts, and localized AI assistance. |
| **Apple Watch** | Direct (Premium Smartwatch) | Advanced sensors (ECG, SpO2), built-in fall detection | High cost (Rp7M–Rp15M+); requires iPhone; complex interface for non-tech-savvy elderly | Low-cost prototype paired with a browser-accessible dashboard independent of smartphone ecosystems. |
| **Wonlex** | Direct (Elderly GPS Watch) | Low price (Rp300k–Rp800k); standalone SOS calling and GPS | No vital sign sensors (SpO2, heart rate, temp); no ML fall detection or AI features | Integrates vital telemetry, ML-based fall detection, and dynamic Gemini AI health analytics. |
