"""End-to-end smoke test for the inference wrapper (train -> save -> load -> predict)."""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from ml.features import extract_features, sliding_labeled_windows
from ml.inference import FallClassifier
from ml.schema import AccelSample, FEATURE_NAMES, HOP_SIZE, LABEL_FALL, WINDOW_SIZE
from ml.synth_data import generate_subject


def _build_windows(sid, seed=3, n_falls=6, n_adl=12):
    samples, labels = generate_subject(sid, seed=seed, n_falls=n_falls, n_adl=n_adl)
    x, y = [], []
    for window, label in sliding_labeled_windows(samples, labels, WINDOW_SIZE, HOP_SIZE):
        features = extract_features(window)
        x.append([features[name] for name in FEATURE_NAMES])
        y.append(label)
    return samples, x, y


def test_save_load_and_predict(tmp_path):
    # Train on several subjects so the tiny smoke-test model generalises.
    x_train, y_train = [], []
    for sid in range(5):
        _, xs, ys = _build_windows(sid)
        x_train.extend(xs)
        y_train.extend(ys)

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=0)),
        ]
    )
    pipeline.fit(x_train, y_train)

    classifier = FallClassifier(pipeline, threshold=0.5, feature_names=FEATURE_NAMES)
    path = tmp_path / "fall_clf.joblib"
    classifier.save(str(path))

    loaded = FallClassifier.load(str(path))
    assert loaded.threshold == classifier.threshold
    assert loaded.feature_names == FEATURE_NAMES

    # A realistic upright window (small tremor on accel + gyro) should NOT be a fall.
    rng = np.random.default_rng(0)
    upright = [
        AccelSample(
            rng.normal(0.0, 0.03),
            rng.normal(0.0, 0.03),
            1.0 + rng.normal(0.0, 0.03),
            rng.normal(0.0, 5.0),
            rng.normal(0.0, 5.0),
            rng.normal(0.0, 5.0),
        )
        for _ in range(WINDOW_SIZE)
    ]
    assert loaded.predict_window(upright).is_fall is False

    # A held-out fall window from a new subject should be a fall.
    samples, labels = generate_subject(9, seed=5, n_falls=6, n_adl=12)
    fall_window = next(
        (
            window
            for window, label in sliding_labeled_windows(samples, labels, WINDOW_SIZE, HOP_SIZE)
            if label == LABEL_FALL
        ),
        None,
    )
    assert fall_window is not None
    assert loaded.predict_window(fall_window).is_fall is True

