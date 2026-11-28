"""Fit a Bradley-Terry-style editorial ranker on explicitly authored preferences."""
import json
from itertools import combinations
from pathlib import Path

import numpy as np
from sklearn.linear_model import LogisticRegression

# Each pair is unique. A fitting row and its inverse stay together.
TRAIN = [
    ("alert", "stale"), ("alert", "flagged"), ("alert", "watch"),
    ("stale", "flagged"), ("stale", "lab"), ("flagged", "watch"),
    ("flagged", "lab"), ("watch", "lab"), ("watch", "simulated"),
    ("lab", "simulated"),
]
TEST = [
    ("alert", "lab"), ("alert", "simulated"), ("stale", "watch"),
    ("stale", "simulated"), ("flagged", "simulated"),
]


def main():
    labels = sorted({item for pair in TRAIN for item in pair})
    assert len({frozenset(pair) for pair in TRAIN + TEST}) == len(list(combinations(labels, 2)))
    basis = dict(zip(labels, np.eye(len(labels))))
    x, y = [], []
    for first, second in TRAIN:
        diff = basis[first] - basis[second]
        x.extend([diff, -diff])
        y.extend([1, 0])
    model = LogisticRegression(fit_intercept=False, C=1, solver="lbfgs").fit(x, y)
    scores = dict(zip(labels, model.coef_[0]))
    correct = sum(scores[a] > scores[b] for a, b in TEST)
    artifact = {"version": 1, "scores": scores, "train_pairs": len(TRAIN),
                "held_out_pairs": len(TEST), "held_out_correct": int(correct)}
    path = Path(__file__).resolve().parents[1] / "app" / "summary_order.json"
    path.write_text(json.dumps(artifact, indent=2) + "\n")
    print(path.read_text())


if __name__ == "__main__":
    main()
