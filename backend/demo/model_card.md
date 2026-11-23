# JagSi simulated vital-trend model

Revision `synthetic-trends-v1`. The FastAPI progress route consumes this local
Random Forest artifact through the existing joblib contract. The artifact hash
in artifacts/metrics.json identifies the exact trained weights.

Each input comprises 60 chronological two-second readings in heart rate (bpm),
SpO2 (%) and temperature (degrees Celsius) order. For each channel the trainer
computes mean, population standard deviation, last-ten minus first-ten mean,
and range. The classifier returns stable, rising_hr, falling_spo2 or
rising_temperature. Below 0.65 maximum class probability the API abstains.
These probabilities are forest scores and have no clinical calibration.

Training used 600 synthetic sessions with one window per session. The
stratified splits contained 300 training, 150 tuning and 150 held-out sessions.
The existing 0.65 gate was fixed before scoring. Held-out macro-F1 was 1.00
and coverage was 100% on single-pattern sessions from the training generator.
Doubling the usual noise on 100 stable windows produced 23 rising-HR outputs,
41 abstentions and 36 correct stable outputs. All 100 mixed HR-up/SpO2-down
windows produced abstentions. A sudden temperature step produced 99 rising
temperature outputs and one abstention. This model describes short simulated
trends. Human recordings, longer-term outcomes and clinical interpretation
require separate evaluation.

From backend run `python -m demo.train_trends` then
`python -m demo.evaluate_trends`. This run used Python 3.14,
scikit-learn 1.7.2, NumPy 2.3.3 and joblib 1.5.2. Regeneration under the
repository's pinned NumPy and joblib versions may produce different bytes.

## Reviewer runbook

Use a fresh checkout of the PR branch so training can regenerate artifacts without overwriting your reference copies. Run these PowerShell commands from the checkout root. Python 3.11 is the project review environment. The recorded artifact was built with the package versions listed above.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
Set-Location backend
Get-FileHash demo/artifacts/trend_model.joblib -Algorithm SHA256
Get-FileHash ml/artifacts/fall_clf.joblib -Algorithm SHA256
..\.venv\Scripts\python.exe -m pytest ml/tests -q
..\.venv\Scripts\python.exe -m demo.evaluate_trends
..\.venv\Scripts\python.exe -m scripts.evaluate_simulated_falls
..\.venv\Scripts\python.exe -m demo.train_trends
```

1. Compare the first hash to `sha256` in `demo/artifacts/metrics.json` and the second to `artifact_sha256` in `ml/artifacts/simulation_evaluation.json`. Do this before retraining. A mismatch means the evidence and local binary need reconciling.
2. The ML test suite produced 21 passes in the training environment. If importing the fall evaluator fails on `paho`, check that the interpreter running the command is the same virtual environment that installed the backend requirements.
3. The trend stress command loads the shipped artifact, applies the backend confidence cutoff, and writes counts per output label to `demo/artifacts/stress_results.json`. Inspect all three scenarios. Correct classification on clean inputs alone misses the noisy-stable failure.
4. The fall command loads the shipped fall artifact, chooses a threshold using seed 2301, then evaluates it once using seed 2302. Its JSON contains the deployed baseline, candidate and per-activity counts. The model card in `../ml/model_card.md` explains the result.
5. The last command fits a 150-tree forest (maximum depth 8, balanced class weights, seed 41) and writes a new trend binary and metrics. Compare the split sizes, class-level support, confusion matrix and coverage. Re-run the stress command to compare the rebuilt artifact with the shipped one. Record package versions and both hashes if they differ.

### How the training examples are constructed

Generator seed 20261118 produces 150 sessions per class. Starting values are drawn uniformly from 65–100 bpm, 95–99% SpO2 and 36–37.2 °C. Independent Gaussian noise has standard deviations of 1.6 bpm, 0.18 percentage points and 0.04 °C. A stable window has zero underlying slope. The other classes add a linear change in one channel over the window: +15 to +35 bpm, a drop of 2.5 to 7 percentage points, or +0.7 to +1.8 °C. Split seeds 41 and 42 reserve 150 test sessions and 150 tuning sessions respectively. Whole sessions stay together. All three splits use the same generator, which limits what the score can demonstrate.

### Handoff to backend and dashboard reviewers

From the backend working directory, the default artifact path is `demo/artifacts/trend_model.joblib`; the backend reads an override from `JAGSI_TREND_MODEL`. The loader checks the ordered feature names and window length. Capture the model revision, confidence, window timestamps and simulated provenance from a live progress response, then compare these with the dashboard for the same device. Include a stale window and an uncertain prediction. Track this evidence under issues #21 and #22. The offline checks above establish model behavior only.
