"""Inference wrapper for the trained fall classifier.

Provides ``FallClassifier``, the single entry point the FastAPI backend will use
to classify a window of MPU6050 samples in production. It loads the trained
artifact and exposes a ``predict_window`` method returning a ``FallResult``.

Expected latency is a few milliseconds on CPU, comfortably within FR2's 5-second
dispatch budget.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

import joblib

from .features import extract_features
from .schema import (
    AccelSample,
    FEATURE_NAMES,
    LABEL_FALL,
    LABEL_NAMES,
    LABEL_NON_FALL,
)


@dataclass(frozen=True)
class FallResult:
    """Outcome of classifying a single motion window."""

    is_fall: bool
    confidence: float  # probability of the fall class in [0, 1]
    label: str
    features: dict = field(default_factory=dict)


class FallClassifier:
    """Loads a trained pipeline and classifies windows of motion samples."""

    def __init__(
        self,
        pipeline,
        threshold: float = 0.5,
        feature_names: Optional[List[str]] = None,
        label_names: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        self.pipeline = pipeline
        self.threshold = threshold
        self.feature_names = list(feature_names) if feature_names else list(FEATURE_NAMES)
        self.label_names = dict(label_names) if label_names else dict(LABEL_NAMES)
        self.metadata = metadata or {}

    # -- persistence ---------------------------------------------------------
    def save(self, path: str) -> None:
        joblib.dump(
            {
                "pipeline": self.pipeline,
                "threshold": self.threshold,
                "feature_names": self.feature_names,
                "label_names": self.label_names,
                "metadata": self.metadata,
            },
            path,
        )

    @classmethod
    def load(cls, path: str) -> "FallClassifier":
        data = joblib.load(path)
        return cls(
            pipeline=data["pipeline"],
            threshold=data["threshold"],
            feature_names=data["feature_names"],
            label_names=data["label_names"],
            metadata=data.get("metadata", {}),
        )

    # -- inference -----------------------------------------------------------
    def predict_proba(self, samples: Sequence[AccelSample]):
        """Return ``(features, [p_non_fall, p_fall])`` for a window."""
        features = extract_features(samples)
        x = [[features[name] for name in self.feature_names]]
        proba = self.pipeline.predict_proba(x)[0]
        return features, proba

    def predict_window(self, samples: Sequence[AccelSample]) -> FallResult:
        """Classify a window of motion samples as fall / non-fall."""
        features, proba = self.predict_proba(samples)
        fall_position = list(self.pipeline.classes_).index(LABEL_FALL)
        p_fall = float(proba[fall_position])
        is_fall = p_fall >= self.threshold
        label = self.label_names[LABEL_FALL if is_fall else LABEL_NON_FALL]
        return FallResult(is_fall=is_fall, confidence=p_fall, label=label, features=features)
