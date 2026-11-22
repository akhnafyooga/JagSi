"""Train and evaluate the JagSi fall-classification model end-to-end.

Usage (from the ``backend/`` directory)::

    python -m ml.train                 # defaults, writes artifacts + model card
    python -m ml.train --help

The pipeline is a scikit-learn ``StandardScaler -> RandomForestClassifier``
trained on synthetic accelerometer/gyroscope windows. The decision threshold is
tuned on a validation split to maximise recall subject to a minimum precision
(safety-critical use). The fitted model, metrics, and a model card are written
to ``backend/ml/artifacts/``.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .features import extract_features, sliding_labeled_windows
from .inference import FallClassifier
from .schema import (
    FEATURE_NAMES,
    HOP_SIZE,
    LABEL_FALL,
    LABEL_NAMES,
    LABEL_NON_FALL,
    WINDOW_SIZE,
)
from .synth_data import generate_subject

PACKAGE_DIR = Path(__file__).resolve().parent
ARTIFACT_DIR = PACKAGE_DIR / "artifacts"
DEFAULT_MODEL_CARD_PATH = PACKAGE_DIR / "model_card.md"


def build_dataset(subject_ids, seed: int, n_falls: int, n_adl: int):
    """Build feature matrix + labels + subject ids from a list of subjects."""
    x_rows, y, subj = [], [], []
    for sid in subject_ids:
        samples, labels = generate_subject(int(sid), seed=seed, n_falls=n_falls, n_adl=n_adl)
        for window, label in sliding_labeled_windows(samples, labels, WINDOW_SIZE, HOP_SIZE):
            features = extract_features(window)
            x_rows.append([features[name] for name in FEATURE_NAMES])
            y.append(label)
            subj.append(sid)
    return np.asarray(x_rows, dtype=float), np.asarray(y, dtype=int), np.asarray(subj, dtype=int)


def _pick_threshold(precisions, recalls, thresholds, min_precision: float) -> float:
    """Choose the threshold that maximises recall subject to min precision."""
    best_threshold = 0.5
    best_recall = -1.0
    for p, r, thr in zip(precisions[:-1], recalls[:-1], thresholds):
        if p >= min_precision and r > best_recall:
            best_recall = r
            best_threshold = float(thr)
    return best_threshold


def _split_subjects(subject_ids: np.ndarray, seed: int):
    order = np.random.default_rng(seed).permutation(subject_ids)
    n_test = max(1, len(subject_ids) // 5)
    n_val = max(1, len(subject_ids) // 5)
    test_ids = order[:n_test]
    val_ids = order[n_test : n_test + n_val]
    train_ids = order[n_test + n_val :]
    return train_ids, val_ids, test_ids


def _evaluate(pipeline, threshold, x, y):
    proba = pipeline.predict_proba(x)[:, 1]
    pred = (proba >= threshold).astype(int)
    return {
        "n_samples": int(len(y)),
        "accuracy": float(accuracy_score(y, pred)),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y, proba)),
        "confusion_matrix": confusion_matrix(y, pred).tolist(),
        "class_balance": {
            LABEL_NAMES[LABEL_NON_FALL]: int((y == LABEL_NON_FALL).sum()),
            LABEL_NAMES[LABEL_FALL]: int((y == LABEL_FALL).sum()),
        },
    }


def build_model_card(metrics: dict) -> str:
    cm = np.asarray(metrics["test"]["confusion_matrix"])
    tn, fp, fn, tp = cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]
    return f"""# Fall Classification Model Card

## Model details
* **Task**: binary fall / impact detection from wearable motion (FR2).
* **Algorithm**: `StandardScaler -> RandomForestClassifier` (scikit-learn).
* **Input**: a `{WINDOW_SIZE}`-sample ({WINDOW_SIZE / 10:.1f}s) window of MPU6050
  accelerometer (g) + gyroscope (deg/s) samples at `10` Hz.
* **Features** (`{len(FEATURE_NAMES)}`): accelerometer SMV statistics, jerk,
  pitch/roll tilt, gyro magnitude, free-fall/impact timing, post-impact inactivity.
* **Output**: `{{is_fall, confidence, label}}`.

## Performance (held-out test subjects)
| Metric | Value |
| --- | --- |
| Threshold | `{metrics['threshold']:.3f}` |
| Test accuracy | `{metrics['test']['accuracy']:.3f}` |
| Test precision | `{metrics['test']['precision']:.3f}` |
| Test recall | `{metrics['test']['recall']:.3f}` |
| Test F1 | `{metrics['test']['f1']:.3f}` |
| Test ROC-AUC | `{metrics['test']['roc_auc']:.3f}` |

Confusion matrix (rows = true, columns = predicted):

| | non_fall | fall |
| --- | ---: | ---: |
| **non_fall** | {tn} | {fp} |
| **fall** | {fn} | {tp} |

## Data
* Synthetic generator (`ml/synth_data.py`) simulating ADL (standing, walking,
  turning, sit/stand, controlled lying) and hard non-falls (abrupt sit, jolt)
  vs. forward/backward/left/right falls (free-fall dip, impact spike, sustained
  post-impact tilt + inactivity).
* **Subject-independent split**: train `{metrics['n_train_subjects']}`, val
  `{metrics['n_val_subjects']}`, test `{metrics['n_test_subjects']}` subjects.

## Limitations
* Trained on **simulated** motion, not clinical or real-world data. It has not
  been validated on human subjects and must not be relied on as a medical device.
* Sampling is fixed at 10 Hz; sharper impacts may be under-sampled.
* A fixed window of 3 s is assumed; streaming integration must buffer samples
  accordingly.

## Intended use
Detect fall impacts from wearable telemetry to trigger caregiver alerts in the
JagSi system. Decision threshold is tuned for high recall subject to
precision >= {metrics['min_precision']:.2f}.
"""


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Train the JagSi fall classifier.")
    parser.add_argument("--subjects", type=int, default=60)
    parser.add_argument("--n-falls", type=int, default=12)
    parser.add_argument("--n-adl", type=int, default=24)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-estimators", type=int, default=300)
    parser.add_argument("--min-precision", type=float, default=0.92)
    parser.add_argument("--out-dir", type=Path, default=ARTIFACT_DIR)
    parser.add_argument("--model-card", type=Path, default=DEFAULT_MODEL_CARD_PATH)
    args = parser.parse_args(argv)

    subject_ids = np.arange(args.subjects)
    train_ids, val_ids, test_ids = _split_subjects(subject_ids, args.seed)

    print(f"Building datasets ({args.subjects} subjects; "
          f"train {len(train_ids)} / val {len(val_ids)} / test {len(test_ids)}) ...")
    x_train, y_train, _ = build_dataset(train_ids, args.seed, args.n_falls, args.n_adl)
    x_val, y_val, _ = build_dataset(val_ids, args.seed, args.n_falls, args.n_adl)
    x_test, y_test, _ = build_dataset(test_ids, args.seed, args.n_falls, args.n_adl)

    print(f"Training RandomForest ({args.n_estimators} trees) on {len(y_train)} windows ...")
    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            (
                "clf",
                RandomForestClassifier(
                    n_estimators=args.n_estimators,
                    class_weight="balanced",
                    random_state=args.seed,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    pipeline.fit(x_train, y_train)

    print("Tuning decision threshold on validation ...")
    val_proba = pipeline.predict_proba(x_val)[:, 1]
    precisions, recalls, thresholds = precision_recall_curve(y_val, val_proba)
    threshold = _pick_threshold(precisions, recalls, thresholds, args.min_precision)
    print(f"Selected threshold = {threshold:.4f}")

    metrics = {
        "n_train_subjects": int(len(train_ids)),
        "n_val_subjects": int(len(val_ids)),
        "n_test_subjects": int(len(test_ids)),
        "min_precision": args.min_precision,
        "threshold": float(threshold),
        "n_estimators": args.n_estimators,
        "feature_names": FEATURE_NAMES,
        "train": _evaluate(pipeline, threshold, x_train, y_train),
        "val": _evaluate(pipeline, threshold, x_val, y_val),
        "test": _evaluate(pipeline, threshold, x_test, y_test),
    }
    test_report = classification_report(
        y_test,
        (pipeline.predict_proba(x_test)[:, 1] >= threshold).astype(int),
        target_names=[LABEL_NAMES[LABEL_NON_FALL], LABEL_NAMES[LABEL_FALL]],
        zero_division=0,
    )
    metrics["classification_report"] = test_report

    args.out_dir.mkdir(parents=True, exist_ok=True)
    model_path = args.out_dir / "fall_clf.joblib"
    metrics_path = args.out_dir / "metrics.json"

    classifier = FallClassifier(
        pipeline,
        threshold=threshold,
        feature_names=FEATURE_NAMES,
        label_names=LABEL_NAMES,
        metadata={"trained_on": "synthetic", "seed": args.seed, "window_seconds": 3.0},
    )
    classifier.save(str(model_path))
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    args.model_card.write_text(build_model_card(metrics), encoding="utf-8")

    print("\n=== Test metrics ===")
    for key in ("accuracy", "precision", "recall", "f1", "roc_auc"):
        print(f"{key:12s}: {metrics['test'][key]:.4f}")
    print(test_report)
    print(f"\nArtifacts written to {args.out_dir}")
    print(f"Model card written to {args.model_card}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


