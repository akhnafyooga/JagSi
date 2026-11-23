"""Evaluate the shipped forest on independent continuous synthetic device sessions.

From backend: python -m scripts.evaluate_simulated_falls
"""
import hashlib
import json
import math
import random
from pathlib import Path

from ml.features import extract_features
from ml.inference import FallClassifier
from ml.retune import Session, choose_threshold, evaluate, per_activity, sweep
from scripts.validate_on_device_windows import fall_samples, still_sample, walking_sample, to_samples


def simulate(seed, classifier):
    random.seed(seed)
    sessions = []
    features = []
    lengths = []
    for activity in ("still", "walking", "sit_down_hard", "lying_down", "fall"):
        for i in range(24):
            phase = random.uniform(0, 10)
            start = random.randint(80, 150)
            generator = walking_sample if activity in ("walking", "fall") else still_sample
            rows = [generator(phase + j / 10) for j in range(300)]
            if activity == "fall":
                rows[start:start + 10] = fall_samples()
                for j in range(start + 10, len(rows)):
                    rows[j] = still_sample(j / 10)
                    rows[j][0], rows[j][2] = rows[j][2], rows[j][0]
            elif activity == "sit_down_hard":
                for offset, bump in enumerate((0.5, 0.7, 0.25)):
                    rows[start + offset][2] += bump
                    rows[start + offset][3] += random.uniform(40, 80)
            elif activity == "lying_down":
                for j in range(start, len(rows)):
                    angle = min(1, (j - start) / 15) * math.pi / 2
                    rows[j][0] += math.sin(angle)
                    rows[j][2] += math.cos(angle) - 1
                    if j < start + 15:
                        rows[j][4] += 60
            samples = to_samples(rows)
            count = 0
            for offset in range(0, len(rows) - 29, 10):
                # A true detection must occur in a window containing the impact.
                if activity == "fall" and not offset <= start + 4 < offset + 30:
                    continue
                vector = extract_features(samples[offset:offset + 30])
                features.append([vector[name] for name in classifier.feature_names])
                count += 1
            sessions.append(Session(f"{seed}-{activity}-{i}", activity, activity == "fall", "simulated"))
            lengths.append(count)
    scores = iter(classifier.pipeline.predict_proba(features)[:, 1])
    for session, length in zip(sessions, lengths):
        session.scores = [float(next(scores)) for _ in range(length)]
    return sessions


if __name__ == "__main__":
    artifact = Path("ml/artifacts/fall_clf.joblib")
    model = FallClassifier.load(artifact)
    selected, reason = choose_threshold(sweep(simulate(2301, model)), .95, .90)
    held_out = simulate(2302, model)
    result = {
        "provenance": "synthetic device sessions, 30 seconds each, 24 per activity per split",
        "tune_seed": 2301, "test_seed": 2302, "selection": reason,
        "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
        "tuning": selected.as_dict(),
        "baseline_test": evaluate(held_out, model.threshold).as_dict(),
        "selected_test": evaluate(held_out, selected.threshold).as_dict(),
        "activities": per_activity(held_out, selected.threshold),
    }
    Path("ml/artifacts/simulation_evaluation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(result["selected_test"])
