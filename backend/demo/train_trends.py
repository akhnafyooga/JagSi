"""Vital-trend model: feature contract and reproducible synthetic training.

Copied from section 9 of docs/wokwi-team-requirements.md so the inference API in
``demo.cloud`` (issue #21) has the exact feature contract to build against and
test with. Training, evaluation, the model card and the artifact hash belong to
issue #20; change the features here only together with that work, because the
API refuses an artifact whose feature list differs from ``FEATURES``.

    python -m demo.train_trends        (run from backend/)

writes demo/artifacts/trend_model.joblib and demo/artifacts/metrics.json.
"""

from pathlib import Path
import hashlib
import json

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

LABELS = ["stable", "rising_hr", "falling_spo2", "rising_temperature"]
FEATURES = [f"{channel}_{stat}" for channel in ["hr", "spo2", "temp"]
            for stat in ["mean", "std", "delta", "range"]]


def features(values):
    values = np.asarray(values, dtype=float)
    if values.shape != (60, 3) or not np.isfinite(values).all():
        raise ValueError("Expected 60 finite [heart_rate, spo2, temperature] rows")
    output = []
    for column in values.T:
        output.extend([column.mean(), column.std(),
                       column[-10:].mean() - column[:10].mean(), np.ptp(column)])
    return np.asarray(output)


def train(output_dir):
    rng = np.random.default_rng(20261118)
    x, y = [], []
    for label in LABELS:
        for session in range(150):
            base = np.array([rng.uniform(65, 100), rng.uniform(95, 99),
                             rng.uniform(36, 37.2)])
            noise = rng.normal(size=(60, 3)) * [1.6, .18, .04]
            change = np.zeros(3)
            if label == "rising_hr":
                change[0] = rng.uniform(15, 35)
            elif label == "falling_spo2":
                change[1] = -rng.uniform(2.5, 7)
            elif label == "rising_temperature":
                change[2] = rng.uniform(.7, 1.8)
            values = base + noise + np.linspace(0, 1, 60)[:, None] * change
            x.append(features(values))
            y.append(label)
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=.25, random_state=41, stratify=y)
    model = RandomForestClassifier(n_estimators=150, max_depth=8,
                                   random_state=41, class_weight="balanced")
    model.fit(x_train, y_train)
    predicted = model.predict(x_test)
    report = classification_report(y_test, predicted, output_dict=True)
    report["confusion_matrix"] = confusion_matrix(
        y_test, predicted, labels=LABELS).tolist()
    report["labels"] = LABELS
    report["provenance"] = "synthetic sessions, one window per session"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = output_dir / "trend_model.joblib"
    joblib.dump({"model": model, "features": FEATURES,
                 "version": "synthetic-trends-v1", "rows": 60}, artifact)
    report["sha256"] = hashlib.sha256(artifact.read_bytes()).hexdigest()
    (output_dir / "metrics.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    train(Path(__file__).resolve().parent / "artifacts")
