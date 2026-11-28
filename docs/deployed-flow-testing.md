# JagSi deployed acceptance test

Use a fresh Google test account and fictional data. Record the Azure URL, Render URL, deployed commit, test time and evidence for each step. Mark each result Pass, Fail or Blocked.

| ID | Action | Expected evidence |
| --- | --- | --- |
| D01 | Open the deployed landing page on desktop and mobile. Open Setup. | Page and navigation load without errors. Google sign-in is enabled. |
| D02 | Start Google sign-in in a private window and complete it with the test account. | Google redirects through Supabase and returns to JagSi /setup. A first-time user sees Akun pengasuh. |
| D03 | Enter a caregiver display name and create fictional wearer Pasien Uji. Select the relationship and complete consent for the fictional scenario. Reload /setup. | Saved account and wearer details persist. Record whether setup resumes at pairing. |
| D04 | Try connecting a watch using a code issued by the deployed backend, if Rafi enabled that flow. | Valid code is accepted once and the setup advances to MCU. If hosted pairing is unavailable, mark Blocked and open /beranda directly for D06. |
| D05 | If hosted MCU is enabled, upload the Quest test image, inspect the raw scan, then review and confirm. Enter the collection date 2014-04-28 manually if absent. | Glucose 115 mg/dL and HbA1c 6.1% carry the lab's H flags. Check HDL's unit and correct to mg/dL if blank. Unconfirmed data is excluded from the brief. If the upload is unavailable, mark Blocked and run the separate local rehearsal. |
| D06 | Open /beranda. Compare two latest responses several seconds apart and open Riwayat. | Timestamps advance, readings are labeled simulated and history shows matching points. Inspect Network for API or CORS failures. |
| D07 | Click Perbarui ringkasan and inspect the daily-brief response. | A brief renders with values traceable to the API. Record local_llm or rules. If D05 passed, the confirmed results have the historic report date and the watch has its own timestamp. Record the actual displayed wearer name. |
| D08 | If a hosted console is enabled, switch to Kritis, pause, resume and trigger SOS. | Abnormal simulated values appear, paused readings become stale after the freshness window, and resuming restores fresh readings. SOS takes priority. Acknowledge and reload to check persistence. Record individual outcomes. |
| D09 | On a separate authorized test account, attempt to access the first account's seeded fictional wearer or watch through the normal app flow. | For production sign-off, access is denied by the backend. Current demo architecture may fail this gate. Record the outcome before considering real data. |

The baseline deployment guide leaves hosted pairing, MCU scanning and remote console controls open. Confirm what was actually enabled before scoring those steps. The local console only controls its own backend. For the local registration, Quest report and SOS walkthrough, use [the Quest rehearsal](new-caregiver-quest-demo.md).

## Result record

| ID | Pass / Fail / Blocked | Actual result | Evidence link |
| --- | --- | --- | --- |
| D01–D09 | | | |

For the presentation, save the successful OAuth return, two fresh simulated samples, and the daily-brief response with its source. Save the local Quest and SOS evidence separately if those flows are local. Crop screenshots to omit account details, credential values and pairing codes.
