# JagSi rehearsal · new caregiver, Quest sample, simulated watch

Use a fresh authorized Google test account for the caregiver. Enter your own display name, then enter **Pasien Uji** as the fictional wearer. Select **Lainnya** and use the consent checkbox for this fictional rehearsal. The Quest page labels the subject TEST, PATIENT. Pasien Uji is the rehearsal alias.

## Before opening the browser

Use the local OAuth-enabled frontend on port 3096 and the simulated backend on port 8013. Enable the pairing preview and console as described in [local setup](local-onboarding-console.md). Start the backend with `JAGSI_ELDER_NAME=Pasien Uji` so the daily brief uses the matching rehearsal name. This is a server-wide setting. OAuth saves the profile in Supabase user metadata. The demo still uses one configured device, and the pairing code does not establish account-level access control. Use a clean browser profile or fresh tab without prior MCU data.

## Run and score

| Step | Action | Expected evidence |
| --- | --- | --- |
| 1 | Open /setup and choose Google sign-in. Create the caregiver and Pasien Uji wearer profiles. | A fresh account opens caregiver registration and continues to wearer setup. |
| 2 | Open /demo-console, choose Stabil / lanjutkan, then Buat kode smartband. Paste the code into setup. | The configured simulated watch pairs with the preview. Continue to MCU. |
| 3 | Upload the attached download.png. Capture OCR output before editing. | Six rows below. The scan returned no date candidates in the local extraction test. |
| 4 | Enter collection date **2014-04-28** manually. Review the rows, confirm, and continue in the same tab. Finish the wrist guide and choose See live. | The old report date and the current simulated watch timestamp remain distinct in the brief. |
| 5 | Refresh Ringkasan AI. Inspect daily-brief in DevTools. | The brief uses Pasien Uji if configured on the server. It reports the two lab flags as historical facts. No high-LDL meal advice is expected. Record local_llm or rules as actually returned. |
| 6 | Switch to Kritis, wait for a new sample, and refresh the brief. Then pause, wait at least 10 seconds after the last accepted sample, and refresh again. | Watch readings update and retain simulation provenance. The paused sample is marked delayed. MCU values and date remain the same. |
| 7 | Click Simulasikan SOS and refresh the brief. Acknowledge the alert in JagSi and resume stable readings. | SOS puts the immediate action first and suppresses routine food guidance while unresolved. Record recovery afterward. |

## Source and observed OCR

| Lab row | Value | Unit | Source range | Flag |
| --- | --- | --- | --- | --- |
| Glucose (scanner label Serum glucose) | 115 | mg/dL | 65–99 | H |
| HbA1c | 6.1 | % of total Hgb (scanner unit %) | <5.7 | H |
| Total cholesterol | 164 | mg/dL | 125–200 | |
| HDL cholesterol | 81 | mg/dL | ≥46 | |
| Triglycerides | 45 | mg/dL | <150 | |
| LDL cholesterol (calculated) | 74 | mg/dL | <130 | |

The HDL unit was blank in the observed OCR output. Correct it to mg/dL before confirmation and record it as an OCR miss. The supplied image is one page of a report. Non-HDL cholesterol, cholesterol/HDL ratio and the personal factors table were outside the extracted six rows. Use the specimen collection date shown on the image. Describe glucose and HbA1c as flagged by the lab on that date.

Save the raw OCR, the reviewed row and date screenshot, the fresh and delayed brief responses, and the SOS response. Mark each step pass, fail or blocked. The image extraction was exercised locally. OAuth and the full browser sequence are rehearsal steps for the presenter.
