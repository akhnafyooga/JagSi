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
