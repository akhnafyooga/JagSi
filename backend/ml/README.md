# JagSi Fall Classification ML Model

Binary fall / impact detector for FR2 ("the cloud backend must process
accelerometer/gyroscope vectors using an ML model to detect fall impacts and
dispatch emergency alerts within 5 seconds").

## Layout

```
ml/
├── schema.py        # telemetry contract, windowing, labels, thresholds
├── synth_data.py    # synthetic MPU6050 motion generator (ADL + falls)
├── features.py      # windowing + feature extraction (pure functions)
├── train.py         # train -> tune threshold -> evaluate -> save artifacts
├── inference.py     # FallClassifier: load artifact + predict_window()
├── artifacts/       # fall_clf.joblib + metrics.json (generated)
└── tests/           # pytest suite
```

## Quickstart

```bash
cd backend
pip install -r requirements-dev.txt

# train and write artifacts + model card
python -m ml.train

# run the test suite
pytest
```

## Inference usage

```python
from ml.inference import FallClassifier

clf = FallClassifier.load("ml/artifacts/fall_clf.joblib")
result = clf.predict_window(samples)  # samples: list[AccelSample] (3s @ 10 Hz)
print(result.is_fall, result.confidence, result.label)
```

## Contract

* **Input**: a 30-sample (3 s) window of `AccelSample` (ax/ay/az in g,
  gx/gy/gz in deg/s) at 10 Hz.
* **Output**: `FallResult(is_fall, confidence, label, features)`.
* **Features**: accelerometer SMV statistics + jerk, pitch/roll tilt, gyro
  magnitude, free-fall/impact timing, post-impact inactivity (see
  `schema.FEATURE_NAMES`).
* **Threshold**: tuned on validation to maximise recall subject to precision
  >= 0.92.

## Notes

* Data is **synthetic** (see `model_card.md` limitations) — it is not clinical
  data.
* The `FallClassifier` interface is the seam the FastAPI backend will consume;
  it has no I/O or framework dependencies beyond `joblib` + `scikit-learn`.
