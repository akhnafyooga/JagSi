# JagSi AI model and caregiver dashboard PRD

**Owner:** Akhnaf, AI engineer. **Status:** proposed for the November 2026 simulation demo. **Consumers:** Rafi (FastAPI and persistence) and Akmal (dashboard and acceptance).

## Product outcome

A caregiver opening JagSi should be able to answer three questions at a glance. What changed during the last observation window? Which event needs my attention first? What can I do next, and why is the app suggesting it? Each answer must carry its observation time and source. A stable two-minute trend describes the readings during those two minutes. It cannot establish overall health.

The release decision covers the team-trained fall and vital-trend models, the Indonesian summary, caregiver warnings and action cards. Disease-risk prediction and individualized nutrition planning would require additional inputs and independent validation. The chatbot can later consume the same structured result.

## Starting point

| Component | Current evidence | Work for this release |
| --- | --- | --- |
| Fall detection | MQTT bridge scores motion windows and records ML alerts. The stored threshold detected 24/24 scripted falls with 94 false alerts. A candidate threshold detected 24/24 with 42 false alerts, all during deliberate lying down. | Improve discrimination on ordinary movements. Keep candidate thresholds experimental until they meet the evaluation gate. Preserve the distinction between ML detection, firmware rules and manual SOS. |
| Vital trends | Shipped Random Forest and progress API classify four patterns. Held-out macro-F1 was 1.00 on 150 sessions from the training generator. Under doubled noise, 23/100 stable windows were classified as rising heart rate. | Test independent sequences, improve noisy-stable behavior and connect the owned model to the summary card. |
| Dashboard text | The summary endpoint supports Gemini and rule-based text. The frontend distinguishes those sources. | Add an explicit JagSi model source, evidence fields and reviewable recommendation content. |

Baseline evidence and reproduction instructions are in the [fall model card](../backend/ml/model_card.md), [trend model card](../backend/demo/model_card.md) and [cloud contract](cloud-inference.md).

## From a sensor reading to a model result

1. **Ingest.** Wokwi publishes motion and vitals through MQTT. The bridge validates the device ID and payload, stamps receipt time and persists accepted observations in SQLite. Retain device, sequence or record ID, units and simulated provenance. Keep the fall alert path local while the worker mirrors committed rows to Supabase.
2. **Score motion.** Supply 30 chronological accelerometer and gyroscope samples at 10 Hz, advancing one second per window. Use the feature order shipped with the fall artifact. Preserve the active threshold, score, model revision and triggering window for each ML alert. Count an incident once across repeated windows when evaluating alerts.
3. **Score vitals.** Read the last 60 chronological cloud readings for one device at approximately two-second intervals. Inputs are heart rate in bpm, SpO₂ in percent and temperature in °C. For each channel compute mean, standard deviation, range and the difference between last-ten and first-ten means. Use the artifact’s exact feature order. Return stable, rising heart rate, falling SpO₂ or rising temperature, or abstain below the configured confidence cutoff (currently 0.65).
4. **Validate before interpretation.** Use the existing checks for incomplete, stale, irregular and missing data. Invalid motion skips fall inference. Invalid vitals clear the previous trend claim. An existing SOS or fall event remains visible when the vitals stream fails.
5. **Compose once.** The summary and progress endpoints share the same inference result for a device and window. Join that result with active alerts and approved guidance. Refresh displayed text when the window, alert acknowledgment, freshness state, model or guidance version changes.

## Model development and evaluation

Train locally on CPU with Python and scikit-learn in the project review environment. Save the joblib artifact, ordered features, data-generator version, package versions, threshold and SHA-256 alongside the model card. Use synthetic sessions and independently scripted Wokwi runs for the demo. Physical validation requires its own evidence.

| Step | Fall model | Vital-trend model |
| --- | --- | --- |
| Label | Label the scripted activity and impact timestamp. Include deliberate lying down, sitting, walking and abrupt ordinary movement. | Label the scripted direction independently of the classifier. Include stable noise, slow ramps, abrupt steps, mixed trends and gaps. Mark ambiguous cases for abstention. |
| Split | Keep every overlapping window from one session in the same split. Reserve separately scripted motion sessions for final evaluation. | Split whole sessions before feature selection. Vary baselines, noise and slopes independently. Reserve teammate-authored scenarios the trainer has never seen. |
| Fit and select | Compare the shipped model against a candidate trained with more difficult non-fall examples. Select the threshold on validation sessions. | Compare the existing forest to the candidate using identical validation sessions. Tune the confidence cutoff while measuring how often the model abstains. |
| Freeze and report | On untouched sessions report detected falls/total, alert precision, false alerts per scored hour and counts by activity. | Report confusion matrix, per-class recall, macro-F1, coverage and false trend calls on noisy-stable sessions. Count abstentions explicitly. |

**Proposed promotion gates.** For fall detection, retain the existing 0.90 precision gate and require recall at least as high as the shipped model on the same evaluation set. Present failed candidates as experimental. For trend classification, propose at most 5 false trend calls in 100 independent noisy-stable sessions, at least 90% coverage on unambiguous single-pattern sessions and at least 85% recall for each trend class, counting abstentions as missed detections. Agree on these proposed trend targets before opening the final test set. Record sample counts and results even if a target is missed.

From a clean checkout, run the shipped baseline before retraining. From the backend directory use `python -m scripts.evaluate_simulated_falls` and `python -m demo.evaluate_trends`. Use `python -m demo.train_trends` for the trend training run and the [fall training guide](../backend/ml/README.md) for the fall pipeline. Keep baseline and candidate artifacts in separate checkouts so results can be reproduced.

## Dashboard behavior and recommendation policy

Warning priority represents **urgency of caregiver attention**. A forest score of 0.9 does not establish a 90% chance of injury or illness. Show the event source, action, timestamp and acknowledgment state. A missing or ambiguous reading must never produce an all-clear message. Pulse oximetry can be inaccurate and requires context, including symptoms. [FDA pulse oximeter guidance](https://www.fda.gov/consumers/consumer-updates/pulse-oximeters-and-oxygen-concentrators-what-know-about-home-oxygen-therapy)

| Condition | Summary or warning | Recommended action |
| --- | --- | --- |
| Fresh, stable window | Describe the time span and measured values. Example: “Pola pembacaan relatif stabil selama dua menit terakhir.” | Offer the history view and last measurement time. |
| Fresh, supported changing trend | Name the channel, direction and observed first/last averages with units. Mark it for review. | Ask the caregiver to check in and verify the reading. Show a saved care-plan instruction only when it applies to this person and situation. |
| SOS or experimental fall event | Give the active event priority over routine cards. Label manual SOS and possible fall distinctly. Keep a visible simulation label for demo runs. | Offer contact and acknowledgment actions. Acknowledgment records a caregiver response and must not assert that the person is safe. |
| High-risk vital warning proposed for future use | Enable only for a documented person-specific care-plan rule with approved thresholds, units, duration, signal-quality conditions and escalation wording. | Display the exact reviewed action and contact pathway. Without an applicable rule, show the observed trend and check-in action. |
| Stale, insufficient, irregular or uncertain data | Explain what prevented interpretation and show the last valid reading time. | Show collection, device or connectivity steps as appropriate. Preserve independent active alerts. |

**Lifestyle and consumption guidance.** Give this its own dashboard section. General education can link to reviewed material on meals, daily activity or hydration. A personalized card can repeat an existing clinician-approved instruction, such as following a saved meal plan, with its author, applicability and review date. Sensor trends alone cannot determine the cause of a change, food restrictions, fluid quantities, supplements, exercise intensity or medication changes. If a plan is missing, expired or conflicting, suppress the personal instruction and offer to view or confirm the care plan. For the demo, use clearly fictional profiles and example plans.

Store each publishable guidance entry with an ID, Indonesian text, intended audience, trigger, source, reviewer, review date and version. Routine guidance must never obscure an active warning. Disable entries that have expired or lack approval. These content and care-plan features are proposed.

## API and presentation contract

Extend the existing `GET /api/devices/{id}/summary` contract. Preserve `text`, `device_id`, `model`, `generated_at`, `based_on` and `error`. Add a source value for the JagSi model and a separate status-only source for windows that cannot produce a prediction. Update the frontend type and source badge together. Keep the existing alert stream available during cloud failure.

| Proposed field | Consumer requirement |
| --- | --- |
| `trend.state`, `trend.label`, `trend.window` | Render observation start/end, units and sample count. Clear the label when the state prevents interpretation. |
| `evidence` | Include telemetry ID bounds, first/last group means, model hash and simulation flag. Every number in the summary must match this window after documented rounding. |
| `warnings[]` | Return event ID, reason, priority, source, timestamp and acknowledgment state. Preserve event identity across refreshes. |
| `recommendations[]` | Include action text, rationale and guidance ID/version. Identify general education, event response and person-specific care-plan content separately. |

**Example acceptance fixture.** Given a simulated fresh rising-HR result, first-ten mean 78 bpm, last-ten mean 94 bpm and no active event, the card reads “Data simulasi. Rata-rata denyut jantung naik dari 78 menjadi 94 bpm selama jendela pengamatan sekitar dua menit.” A check-in action appears. No disease or diet claim appears. Stop the feed and verify the card replaces the trend with stale status. Trigger SOS during the outage and verify the warning remains actionable.

## Acceptance and ownership

| Owner | Deliverable | Sign-off evidence |
| --- | --- | --- |
| Akhnaf, AI | Two versioned artifacts, thresholds, independently labeled scenarios, baseline/candidate report and summary wording keyed to output state. | Replay a saved window, reproduce the output and explain one false positive and one abstention. Mark each model gate passed or failed. |
| Rafi, backend | Shared inference service, summary schema, priority and guidance selection, provenance and freshness handling. | Contract tests for all model states, cloud failure, active SOS with stale vitals, and missing or expired plan. Every fixture returns the expected warning and guidance IDs. |
| Akmal, dashboard | Indonesian summary, prominent warning, source and time labels, acknowledgment and reviewed action cards. | Trace every displayed number to a response. Test refresh, two-tab acknowledgment, stale recovery and simulated labeling. Capture screenshots and a timed fall demo. |

At rehearsal use one candidate commit, device and model hash per artifact. Record hosted or local database target and test IDs. Require all scripted summary numbers and units to match the underlying response, zero stale predictions displayed as current, and zero personal consumption instructions without an applicable reviewed plan. Time fall alert delivery from backend receipt of the final required sample to the visible alert against the project target of five seconds. Record failures alongside successful scenarios. A demo pass supports claims about those simulated scenarios only.

**Release order:** deliver the model-backed summary first, then source-labeled event warnings, then reviewed action cards. Person-specific clinical warning rules and consumption guidance remain future work until their inputs, review process and validation are in place. [Shared integration plan](finalization-week.md)
