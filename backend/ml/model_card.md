# Fall Classification Model Card

## Model details
* **Task**: binary fall / impact detection from wearable motion (FR2).
* **Algorithm**: `StandardScaler -> RandomForestClassifier` (scikit-learn).
* **Input**: a `30`-sample (3.0s) window of MPU6050
  accelerometer (g) + gyroscope (deg/s) samples at `10` Hz.
* **Features** (`18`): accelerometer SMV statistics, jerk,
  pitch/roll tilt, gyro magnitude, free-fall/impact timing, post-impact inactivity.
* **Output**: `{is_fall, confidence, label}`.

## Performance (held-out test subjects)
| Metric | Value |
| --- | --- |
| Threshold | `0.110` |
| Test accuracy | `0.957` |
| Test precision | `0.914` |
| Test recall | `0.985` |
| Test F1 | `0.949` |
| Test ROC-AUC | `0.996` |

Confusion matrix (rows = true, columns = predicted):

| | non_fall | fall |
| --- | ---: | ---: |
| **non_fall** | 849 | 57 |
| **fall** | 9 | 609 |

## Data
* Synthetic generator (`ml/synth_data.py`) simulating ADL (standing, walking,
  turning, sit/stand, controlled lying) and hard non-falls (abrupt sit, jolt)
  vs. forward/backward/left/right falls (free-fall dip, impact spike, sustained
  post-impact tilt + inactivity).
* **Subject-independent split**: train `36`, val
  `12`, test `12` subjects.

## Limitations
* Trained on **simulated** motion, not clinical or real-world data. It has not
  been validated on human subjects and must not be relied on as a medical device.
* Sampling is fixed at 10 Hz; sharper impacts may be under-sampled.
* A fixed window of 3 s is assumed; streaming integration must buffer samples
  accordingly.

## Intended use
Detect fall impacts from wearable telemetry to trigger caregiver alerts in the
JagSi system. Decision threshold is tuned for high recall subject to
precision >= 0.92.
