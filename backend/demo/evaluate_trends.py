"""Probe the saved vital-trend artifact with noisy, mixed and step inputs."""
import json
from pathlib import Path

import joblib
import numpy as np

from demo.train_trends import FEATURES, features


def main():
    directory = Path(__file__).parent / "artifacts"
    artifact = joblib.load(directory / "trend_model.joblib")
    assert artifact["features"] == FEATURES and artifact["rows"] == 60
    rng = np.random.default_rng(2303)
    model = artifact["model"]
    slope = np.linspace(0, 1, 60)
    cases = {
        "noisy_stable": (slope, [0, 0, 0]),
        "mixed_hr_up_spo2_down": (slope, [22, -4, 0]),
        "step_temperature": ((slope >= .5).astype(float), [0, 0, 1.1]),
    }
    report = {}
    for name, (shape, change) in cases.items():
        noise = rng.normal(size=(100, 60, 3)) * [3.2, .36, .08]
        windows = [82, 97, 36.5] + shape[:, None] * change + noise
        probs = model.predict_proba([features(window) for window in windows])
        labels = np.where(probs.max(axis=1) >= .65, model.classes_[probs.argmax(axis=1)], "uncertain")
        report[name] = {str(label): int(sum(labels == label)) for label in np.unique(labels)}
    (directory / "stress_results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report)


if __name__ == "__main__":
    main()
