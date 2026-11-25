# JagSi AI integration | Technical report

**Author role:** Akhnaf, AI engineer. **Implementation reviewed:** commit `3cd3d10`, 25 November 2026.

## Abstract

JagSi uses two team-trained Random Forest classifiers to interpret simulated wearable data. One detects possible falls from three seconds of motion. The other classifies trends in approximately two minutes of vital readings. The caregiver dashboard uses the vital-trend prediction to produce an Indonesian summary grounded in the recorded measurements. The experiments demonstrate that both models can recognize scripted patterns. They also reveal two failure modes that matter for caregivers: deliberate lying down can trigger a fall alert, and noisy readings can resemble a rising heart rate.

## Methods

| Design choice | Fall detection | Vital-trend classification |
| --- | --- | --- |
| Input | 30 accelerometer and gyroscope samples at 10 Hz | 60 readings at roughly two-second intervals for heart rate, SpO₂ and temperature |
| Training data | Synthetic falls, routine activities and abrupt non-fall movements. Separate simulated subjects for training (36), validation (12) and testing (12). | 600 synthetic single-pattern sessions, split into 300 training, 150 tuning and 150 held-out sessions. All three splits came from the same generator. |
| Features and estimator | 18 motion features describe acceleration magnitude, jerk, tilt, rotation, impact timing and inactivity. A scikit-learn pipeline scales the features and fits a Random Forest. | Each channel contributes its mean, standard deviation, range and difference between the last-ten and first-ten means. A 150-tree scikit-learn Random Forest classifies the resulting 12 features. |
| Output | Fall score and threshold decision. The bridge can create an alert with an ML source and an event ID. Manual SOS and firmware-rule alerts have separate origins. | Stable, rising heart rate, falling SpO₂ or rising temperature. A maximum class score below 0.65 produces an uncertain result. |

The training scripts, feature definitions, environment details and reproduction commands are available in the [fall model card](../backend/ml/model_card.md) and [trend model card](../backend/demo/model_card.md).

## Results and interpretation

| Evaluation | Recorded result | What the experiment establishes |
| --- | --- | --- |
| Vital trends, held-out clean sessions | Macro-F1 1.00 across 150 sessions, with 100% coverage | The classifier distinguished all four patterns produced by this generator. Macro-F1 gives each class equal weight. |
| Vital trends, 100 stable sessions with doubled noise | 36 stable, 23 rising heart rate, 41 uncertain | The model sometimes treats noise as directional change. Reporting how often it abstains is necessary to interpret its accuracy. |
| Fall detection, held-out scripted events | At the stored threshold of 0.11, 24/24 falls detected and 94 false alerts. Alert precision was 0.203. | High detection of scripted falls came with a substantial false-alert burden. Precision counts the proportion of raised alerts that corresponded to a scripted fall. |
| Fall threshold experiment | At 0.95, 24/24 falls detected and 42 false alerts, all from deliberate lying down. Precision was 0.364. | The candidate missed the project’s 0.90 precision target and the stored threshold remained in place. |

These measurements describe synthetic sessions. Human fall detection, clinical risk estimation and individualized dietary recommendations require separate evidence. [Trend metrics](../backend/demo/artifacts/metrics.json) · [Noise stress results](../backend/demo/artifacts/stress_results.json) · [Fall event evaluation](../backend/ml/artifacts/simulation_evaluation.json)

## Dashboard implementation and verification

Wokwi publishes readings through MQTT. The backend stores accepted readings in SQLite and mirrors them to cloud storage. The progress API selects the latest 60 vital readings for one device, checks their quality and scores the window. The home-screen card requests this result and renders Indonesian text using the predicted label, observation period and measured averages. The model identifies the pattern. The application supplies the wording. An uncertain result gets neutral text, and a stale or unavailable feed clears the earlier trend claim. [Backend inference](../backend/demo/cloud.py) · [Dashboard data flow](../frontend/lib/useAiSummary.ts) · [Summary wording](../frontend/lib/trendSummary.ts)

Verification recorded for commit `3cd3d10` included 60 passing frontend tests, 21 passing model tests and a passing TypeScript check. The new summary tests cover measured values, model attribution and suppression of stale or uncertain claims. An earlier cloud check used a local PostgreSQL stand-in. A live Wokwi-to-hosted-Supabase run with the updated dashboard remained pending at this revision. [Summary tests](../frontend/lib/__tests__/trendSummary.test.ts) · [Cloud verification record](evidence/wokwi-owned-ai/README.md)

## Conclusion

The strongest demonstrated result is traceability. A reviewer can connect a trend sentence to the selected device, model revision and measured window. The next model experiment should add noisy stable sessions and a wider range of deliberate lying-down movements, then evaluate fresh scenarios independently scripted by another teammate. The next integration check should capture one timestamped reading, the corresponding API response and the dashboard card during the same run. [AI requirements and proposed release criteria](ai-model-prd.md)
