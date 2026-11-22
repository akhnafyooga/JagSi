"""Window segmentation and feature extraction for fall classification.

All functions are pure (no I/O, no random state) so they can be unit-tested in
isolation. The feature set mirrors the physical characteristics described in the
README: accelerometer spikes, pitch/roll (tilt), and impact-related movement.
"""

from __future__ import annotations

import math
from typing import List, Sequence

from .schema import (
    AccelSample,
    FEATURE_NAMES,
    FREE_FALL_G_THRESHOLD,
    IMPACT_G_THRESHOLD,
    INACTIVITY_SECONDS,
    LABEL_FALL,
    LABEL_NON_FALL,
    SAMPLE_RATE_HZ,
)

FeatureVector = dict[str, float]


def smv(ax: float, ay: float, az: float) -> float:
    """Signal magnitude vector of the accelerometer (g)."""
    return math.sqrt(ax * ax + ay * ay + az * az)


def gyro_magnitude(gx: float, gy: float, gz: float) -> float:
    """Magnitude of the gyroscope angular velocity (deg/s)."""
    return math.sqrt(gx * gx + gy * gy + gz * gz)


def pitch_degrees(ay: float, az: float) -> float:
    """Pitch (degrees), rotation about the x-axis."""
    return math.degrees(math.atan2(ay, az))


def roll_degrees(ax: float, ay: float, az: float) -> float:
    """Roll (degrees), rotation about the y-axis."""
    return math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    m = _mean(values)
    return math.sqrt(sum((v - m) ** 2 for v in values) / len(values))


def _longest_run_below(values: Sequence[float], threshold: float) -> int:
    best = 0
    cur = 0
    for v in values:
        if v < threshold:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def _longest_run_above(values: Sequence[float], threshold: float) -> int:
    best = 0
    cur = 0
    for v in values:
        if v > threshold:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def extract_features(samples: Sequence[AccelSample]) -> FeatureVector:
    """Extract a fixed-size feature vector from a window of motion samples.

    Returns a dict keyed by ``FEATURE_NAMES``. An empty window returns all-zero
    features so that callers never crash on degenerate input.
    """
    n = len(samples)
    if n == 0:
        return {name: 0.0 for name in FEATURE_NAMES}

    smvs = [smv(s.ax, s.ay, s.az) for s in samples]
    gyros = [gyro_magnitude(s.gx, s.gy, s.gz) for s in samples]
    pitches = [pitch_degrees(s.ay, s.az) for s in samples]
    rolls = [roll_degrees(s.ax, s.ay, s.az) for s in samples]

    # Jerk = rate of change of SMV (g/s), taken in absolute value.
    jerks = [abs(smvs[i] - smvs[i - 1]) * SAMPLE_RATE_HZ for i in range(1, n)]

    free_fall_min = min(smvs)
    free_fall_duration = _longest_run_below(smvs, FREE_FALL_G_THRESHOLD) / SAMPLE_RATE_HZ
    impact_duration = _longest_run_above(smvs, IMPACT_G_THRESHOLD) / SAMPLE_RATE_HZ

    k = max(1, int(INACTIVITY_SECONDS * SAMPLE_RATE_HZ))
    tail = smvs[-k:] if n >= k else smvs
    post_std = _std(tail)

    return {
        "smv_mean": _mean(smvs),
        "smv_max": max(smvs),
        "smv_min": min(smvs),
        "smv_std": _std(smvs),
        "smv_peak_to_peak": max(smvs) - min(smvs),
        "jerk_max": max(jerks) if jerks else 0.0,
        "jerk_mean": _mean(jerks),
        "pitch_mean": _mean(pitches),
        "pitch_range": max(pitches) - min(pitches),
        "roll_mean": _mean(rolls),
        "roll_range": max(rolls) - min(rolls),
        "tilt_change": abs(pitches[-1] - pitches[0]) + abs(rolls[-1] - rolls[0]),
        "gyro_max": max(gyros),
        "gyro_mean": _mean(gyros),
        "free_fall_min": free_fall_min,
        "free_fall_duration": free_fall_duration,
        "impact_duration": impact_duration,
        "post_std": post_std,
    }


def sliding_windows(
    samples: Sequence[AccelSample], window_size: int, hop_size: int
) -> List[List[AccelSample]]:
    """Segment a stream into overlapping windows.

    Windows are contiguous slices of ``window_size`` samples, advanced by
    ``hop_size``. A trailing partial window is discarded.
    """
    windows: List[List[AccelSample]] = []
    for start in range(0, len(samples) - window_size + 1, hop_size):
        windows.append(list(samples[start : start + window_size]))
    return windows


def sliding_labeled_windows(
    samples: Sequence[AccelSample],
    labels: Sequence[int],
    window_size: int,
    hop_size: int,
) -> List[tuple]:
    """Segment a stream into ``(window, label)`` pairs.

    A window is labelled fall if *any* of its samples is fall-labelled; this
    aligns the label with the impact event the window is centred on. Samples and
    labels must be the same length.
    """
    pairs: List[tuple] = []
    for start in range(0, len(samples) - window_size + 1, hop_size):
        window = list(samples[start : start + window_size])
        window_labels = labels[start : start + window_size]
        label = LABEL_FALL if any(l == LABEL_FALL for l in window_labels) else LABEL_NON_FALL
        pairs.append((window, label))
    return pairs
