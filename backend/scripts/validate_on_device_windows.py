#!/usr/bin/env python3
"""Measures the fall classifier against windows shaped like the device sends.

Why this exists. The figures reported for issue #9 (recall 0.985, precision
0.914) were measured on windows produced by ``ml/synth_data.py``, the same module
that produced the training data. That answers "does the model fit its own
generator", not "does it work on what the watch publishes". This script asks the
second question, using the motion generator in ``tools/fake_device.py``, which is
written to match the firmware payload rather than the training set.

Run from backend/:

    python3 scripts/validate_on_device_windows.py --windows 300

Reported numbers are a sanity check, not a clinical validation. The honest
ceiling here is still synthetic data: real validation needs recordings from the
physical MPU6050 with labelled activities.
"""

from __future__ import annotations

import argparse
import collections
import random
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND.parent / "tools"))

import warnings  # noqa: E402

warnings.filterwarnings("ignore")

from fake_device import (  # noqa: E402
    MOTION_WINDOW_SIZE,
    fall_samples,
    still_sample,
    walking_sample,
)

from app.config import settings  # noqa: E402
from ml.inference import FallClassifier  # noqa: E402
from ml.schema import AccelSample  # noqa: E402


def to_samples(rows):
    return [
        AccelSample(ax=r[0], ay=r[1], az=r[2], gx=r[3], gy=r[4], gz=r[5]) for r in rows
    ]


def still_window(t0):
    return [still_sample(t0 + i * 0.1) for i in range(MOTION_WINDOW_SIZE)]


def walking_window(t0):
    return [walking_sample(t0 + i * 0.1) for i in range(MOTION_WINDOW_SIZE)]


def fall_window(t0):
    """20 samples of normal activity, then the 10-sample fall pattern."""
    lead = [walking_sample(t0 + i * 0.1) for i in range(MOTION_WINDOW_SIZE - 10)]
    return lead + fall_samples()


def sit_to_stand_window(t0):
    """A hard non-fall: a brisk sit-to-stand produces a real acceleration bump
    and a large tilt change, which is what trips naive threshold rules."""
    rows = [still_sample(t0 + i * 0.1) for i in range(12)]
    rows += [
        [0.35, 0.25, 1.55, 60.0, 45.0, 20.0],
        [0.45, 0.30, 1.70, 80.0, 55.0, 25.0],
        [0.20, 0.15, 1.25, 40.0, 30.0, 15.0],
    ]
    rows += [still_sample(t0 + (15 + i) * 0.1) for i in range(MOTION_WINDOW_SIZE - 15)]
    return rows[:MOTION_WINDOW_SIZE]


SCENARIOS = {
    "still (sitting)": (still_window, False),
    "walking": (walking_window, False),
    "sit-to-stand": (sit_to_stand_window, False),
    "fall": (fall_window, True),
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--windows", type=int, default=200, help="windows per scenario")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="override the stored decision threshold",
    )
    args = parser.parse_args()
    random.seed(args.seed)

    classifier = FallClassifier.load(settings.model_path)
    threshold = args.threshold if args.threshold is not None else classifier.threshold
    classifier.threshold = threshold

    print(f"\nModel:     {settings.model_path}")
    print(f"Threshold: {threshold}")
    print(f"Windows:   {args.windows} per scenario, 3 s each at 10 Hz\n")

    header = f"{'scenario':<18}{'windows':>9}{'flagged':>9}{'rate':>9}{'mean conf':>11}"
    print(header)
    print("-" * len(header))

    totals = collections.Counter()
    per_scenario = {}

    for name, (maker, is_fall) in SCENARIOS.items():
        flagged = 0
        confidences = []
        for i in range(args.windows):
            result = classifier.predict_window(to_samples(maker(i * 3.0)))
            confidences.append(result.confidence)
            if result.is_fall:
                flagged += 1
        rate = flagged / args.windows
        per_scenario[name] = (flagged, rate, sum(confidences) / len(confidences))
        print(
            f"{name:<18}{args.windows:>9}{flagged:>9}{rate:>8.1%}"
            f"{sum(confidences) / len(confidences):>11.3f}"
        )

        if is_fall:
            totals["tp"] += flagged
            totals["fn"] += args.windows - flagged
        else:
            totals["fp"] += flagged
            totals["tn"] += args.windows - flagged

    tp, fn, fp, tn = totals["tp"], totals["fn"], totals["fp"], totals["tn"]
    recall = tp / (tp + fn) if tp + fn else 0.0
    precision = tp / (tp + fp) if tp + fp else 0.0

    print("\n" + "-" * len(header))
    print(f"recall      {recall:.3f}   (target from issue #9: >= 0.95)")
    print(f"precision   {precision:.3f}   (target from issue #9: >= 0.90)")
    print(f"confusion   TP {tp}  FN {fn}  FP {fp}  TN {tn}")

    # What a caregiver would actually experience. Windows arrive every second.
    non_fall_rate = fp / (fp + tn) if fp + tn else 0.0
    per_hour = non_fall_rate * 3600
    print(
        f"\nFalse alerts while nothing is wrong: {non_fall_rate:.1%} of windows, "
        f"about {per_hour:.0f} per hour per device"
    )
    print("(one window per second; backend cooldown collapses bursts, not the rate)")

    if recall < 0.95 or precision < 0.90:
        print("\nAt least one issue #9 target is not met on device-shaped windows.")
        return 1
    print("\nBoth issue #9 targets hold on device-shaped windows.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
