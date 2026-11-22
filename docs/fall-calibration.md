# Fall Model Calibration Protocol

This protocol defines how to evaluate the fall classifier on physical MPU6050 recordings for [issue #9](https://github.com/akhnafyooga/JagSi/issues/9).

The published [Week 6 validation](https://github.com/akhnafyooga/JagSi/blob/b6278df5fbc6444be805a0cb0970a5b24665981f/docs/week6-validation.md#the-finding-that-matters) used firmware-shaped synthetic windows. At the stored threshold of 0.11, it reported 0.401 precision and flagged 192 of 200 walking windows. Use this result as a regression baseline for false positives.

## Record and split the sessions

1. Capture chronological 30-sample windows at 10 Hz with all three accelerometer axes in g and three gyroscope axes in degrees per second. Record the sensor placement, device and firmware revision, session ID, anonymized participant ID, activity, and event time where applicable.
2. Capture walking, stairs, sitting down, deliberate lying down and stationary sessions. Include hard negatives such as abrupt sitting. Use a padded test rig for preliminary impact checks and follow the team's approved lab procedure for any human-participant recording. Record test-rig and human sessions separately.
3. Reject malformed or incomplete windows and record the exclusion counts. Keep overlapping windows within their originating session. Assign whole participants to tuning or holdout before sweeping thresholds.

## Choose the operating threshold

1. Sweep candidate thresholds on the tuning split using the current classifier. Score recall per labelled fall event and count alerts after applying the backend's 15-second cooldown. Compute alert precision and false alerts per hour of non-fall recordings.
2. Freeze the candidate, then run the held-out split once. Report the threshold, model revision, participant and session counts, total non-fall duration, fall recall, alert precision and false alerts per hour. The issue targets are at least 0.95 fall recall and 0.90 alert precision. Report activities separately so a high false-alert rate during walking stays visible.
3. Attach the evaluation to #9. Update the model card and confirm the active threshold at `/api/health` after any approved deployment change. If the held-out targets are missed, record the result and keep calibration open.
