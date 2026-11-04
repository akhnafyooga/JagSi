"""Synthetic accelerometer/gyroscope data generator for fall classification.

Generates deterministic, multi-subject time series of MPU6050-style motion:

  * non-fall activities of daily living (ADL): standing, walking, turning,
    sitting down / standing up, lying down slowly, and *hard non-falls*
    (abrupt heavy sit, sharp jolt that recovers upright).
  * falls: forward, backward, left and right falls with the classic
    free-fall dip -> impact spike -> sustained post-impact tilt + inactivity.

Output is a stream of samples paired with per-sample labels. ``train.py``
segments these into labelled windows.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from .schema import AccelSample, LABEL_FALL, LABEL_NON_FALL, SAMPLE_RATE_HZ


def _noise(rng: np.random.Generator, n: int, scale: float) -> np.ndarray:
    return rng.normal(0.0, scale, n)


def _stationary(
    rng: np.random.Generator, n: int, base: Tuple[float, float, float] = (0.0, 0.0, 1.0)
) -> Tuple[np.ndarray, ...]:
    """A near-still posture (upright or lying) with small tremor."""
    ax0, ay0, az0 = base
    ax = np.full(n, ax0) + _noise(rng, n, 0.03)
    ay = np.full(n, ay0) + _noise(rng, n, 0.03)
    az = np.full(n, az0) + _noise(rng, n, 0.03)
    gx = _noise(rng, n, 5.0)
    gy = _noise(rng, n, 5.0)
    gz = _noise(rng, n, 5.0)
    return ax, ay, az, gx, gy, gz


def _walking(rng: np.random.Generator, n: int, dt: float) -> Tuple[np.ndarray, ...]:
    """Walking with a periodic gait oscillation."""
    t = np.arange(n) * dt
    f = rng.uniform(0.8, 1.6)
    ax = 0.15 * np.sin(2 * np.pi * f * t) + _noise(rng, n, 0.04)
    ay = 0.12 * np.sin(2 * np.pi * 0.5 * f * t + 1.0) + _noise(rng, n, 0.04)
    az = 1.0 + 0.2 * np.sin(2 * np.pi * 2.0 * f * t) + _noise(rng, n, 0.04)
    gx = 40.0 * np.sin(2 * np.pi * f * t) + _noise(rng, n, 10.0)
    gy = 30.0 * np.sin(2 * np.pi * 0.5 * f * t + 1.0) + _noise(rng, n, 10.0)
    gz = 25.0 * np.sin(2 * np.pi * 2.0 * f * t) + _noise(rng, n, 10.0)
    return ax, ay, az, gx, gy, gz


def _transition(
    rng: np.random.Generator,
    n: int,
    start: Tuple[float, float, float],
    end: Tuple[float, float, float],
) -> Tuple[np.ndarray, ...]:
    """Smooth linear orientation change (e.g. sitting, controlled lying)."""
    ax = np.linspace(start[0], end[0], n) + _noise(rng, n, 0.05)
    ay = np.linspace(start[1], end[1], n) + _noise(rng, n, 0.05)
    az = np.linspace(start[2], end[2], n) + _noise(rng, n, 0.05)
    gx = _noise(rng, n, 8.0)
    gy = _noise(rng, n, 8.0)
    gz = _noise(rng, n, 8.0)
    return ax, ay, az, gx, gy, gz


class _StreamBuilder:
    """Accumulates per-axis samples and per-sample labels."""

    def __init__(self, dt: float) -> None:
        self.dt = dt
        self.ax: List[float] = []
        self.ay: List[float] = []
        self.az: List[float] = []
        self.gx: List[float] = []
        self.gy: List[float] = []
        self.gz: List[float] = []
        self.labels: List[int] = []

    def add(
        self,
        ax: np.ndarray,
        ay: np.ndarray,
        az: np.ndarray,
        gx: np.ndarray,
        gy: np.ndarray,
        gz: np.ndarray,
        label: int,
    ) -> None:
        n = len(ax)
        self.ax.extend(np.asarray(ax, dtype=float).tolist())
        self.ay.extend(np.asarray(ay, dtype=float).tolist())
        self.az.extend(np.asarray(az, dtype=float).tolist())
        self.gx.extend(np.asarray(gx, dtype=float).tolist())
        self.gy.extend(np.asarray(gy, dtype=float).tolist())
        self.gz.extend(np.asarray(gz, dtype=float).tolist())
        self.labels.extend([label] * n)

    def to_samples(self) -> Tuple[List[AccelSample], List[int]]:
        n = len(self.ax)
        samples = [
            AccelSample(
                ax=self.ax[i],
                ay=self.ay[i],
                az=self.az[i],
                gx=self.gx[i],
                gy=self.gy[i],
                gz=self.gz[i],
                t=i / SAMPLE_RATE_HZ,
            )
            for i in range(n)
        ]
        return samples, self.labels


_FALL_POST_ORIENTATION = {
    "forward": (-0.9, 0.0, 0.15),
    "backward": (0.9, 0.0, 0.15),
    "left": (0.0, -0.9, 0.15),
    "right": (0.0, 0.9, 0.15),
}


def _add_fall(builder: _StreamBuilder, rng: np.random.Generator, dt: float, direction: str) -> None:
    post = _FALL_POST_ORIENTATION[direction]

    pre_n = int(rng.uniform(0.5, 1.0) * SAMPLE_RATE_HZ)
    ff_n = int(rng.uniform(0.25, 0.5) * SAMPLE_RATE_HZ)
    imp_n = max(1, int(rng.uniform(0.1, 0.2) * SAMPLE_RATE_HZ))
    post_n = int(rng.uniform(1.0, 2.0) * SAMPLE_RATE_HZ)

    # 1) pre-impact: upright (still an ADL posture)
    builder.add(*_stationary(rng, pre_n), label=LABEL_NON_FALL)

    # 2) free fall: SMV dips toward ~0.2 g as acceleration approaches zero
    ff_ax = np.linspace(0.0, post[0] * 0.3, ff_n) + _noise(rng, ff_n, 0.06)
    ff_ay = np.linspace(0.0, post[1] * 0.3, ff_n) + _noise(rng, ff_n, 0.06)
    ff_az = np.linspace(1.0, 0.2, ff_n) + _noise(rng, ff_n, 0.06)
    builder.add(
        ff_ax, ff_ay, ff_az,
        _noise(rng, ff_n, 40.0), _noise(rng, ff_n, 40.0), _noise(rng, ff_n, 40.0),
        label=LABEL_FALL,
    )

    # 3) impact: sharp decaying spike (2-4 g) plus a gyro burst
    peak = rng.uniform(2.0, 4.0)
    decay = np.exp(-3.0 * np.arange(imp_n) / max(imp_n, 1))
    imp_ax = np.full(imp_n, post[0] * 0.4) + _noise(rng, imp_n, 0.1)
    imp_ay = np.full(imp_n, post[1] * 0.4) + _noise(rng, imp_n, 0.1)
    imp_az = 0.3 + peak * decay + _noise(rng, imp_n, 0.1)
    gyro_peak = rng.uniform(200.0, 400.0)
    builder.add(
        imp_ax, imp_ay, imp_az,
        gyro_peak * decay + _noise(rng, imp_n, 20.0),
        gyro_peak * decay * 0.7 + _noise(rng, imp_n, 20.0),
        gyro_peak * decay * 0.5 + _noise(rng, imp_n, 20.0),
        label=LABEL_FALL,
    )

    # 4) post-impact: sustained lying tilt with low motion
    post_ax = np.full(post_n, post[0]) + _noise(rng, post_n, 0.05)
    post_ay = np.full(post_n, post[1]) + _noise(rng, post_n, 0.05)
    post_az = np.full(post_n, post[2]) + _noise(rng, post_n, 0.05)
    builder.add(
        post_ax, post_ay, post_az,
        _noise(rng, post_n, 8.0), _noise(rng, post_n, 8.0), _noise(rng, post_n, 8.0),
        label=LABEL_FALL,
    )


def _add_adl(builder: _StreamBuilder, rng: np.random.Generator, dt: float, kind: str) -> None:
    n = int(rng.uniform(1.5, 4.0) * SAMPLE_RATE_HZ)

    if kind == "stand":
        builder.add(*_stationary(rng, n), label=LABEL_NON_FALL)

    elif kind == "walk":
        builder.add(*_walking(rng, n, dt), label=LABEL_NON_FALL)

    elif kind == "turn":
        ang = np.linspace(0, rng.uniform(60.0, 180.0), n) * np.pi / 180.0
        ax = 0.1 * np.sin(ang) + _noise(rng, n, 0.04)
        ay = 0.1 * np.cos(ang) + _noise(rng, n, 0.04)
        az = np.full(n, 1.0) + _noise(rng, n, 0.04)
        gz = np.full(n, 120.0) + _noise(rng, n, 10.0)
        builder.add(ax, ay, az, _noise(rng, n, 8.0), _noise(rng, n, 8.0), gz, label=LABEL_NON_FALL)

    elif kind == "sit_stand":
        seg = max(1, n // 2)
        builder.add(*_transition(rng, seg, (0.0, 0.0, 1.0), (0.0, 0.3, 0.85)), label=LABEL_NON_FALL)
        builder.add(*_transition(rng, n - seg, (0.0, 0.3, 0.85), (0.0, 0.0, 1.0)), label=LABEL_NON_FALL)

    elif kind == "lie_down":
        seg1 = max(1, int(n * 0.3))
        seg2 = max(1, int(n * 0.4))
        seg3 = max(1, n - seg1 - seg2)
        builder.add(*_transition(rng, seg1, (0.0, 0.0, 1.0), (0.0, 0.0, 0.15)), label=LABEL_NON_FALL)
        builder.add(*_stationary(rng, seg2, base=(0.0, 0.0, 0.15)), label=LABEL_NON_FALL)
        builder.add(*_transition(rng, seg3, (0.0, 0.0, 0.15), (0.0, 0.0, 1.0)), label=LABEL_NON_FALL)

    elif kind == "hard_sit":
        # abrupt downward bump that settles into a seated lean (hard negative)
        seg1 = max(1, int(n * 0.4))
        seg2 = max(1, int(n * 0.2))
        seg3 = max(1, n - seg1 - seg2)
        builder.add(*_stationary(rng, seg1), label=LABEL_NON_FALL)
        peak = rng.uniform(1.8, 2.5)
        decay = np.exp(-3.0 * np.arange(seg2) / max(seg2, 1))
        builder.add(
            _noise(rng, seg2, 0.05),
            _noise(rng, seg2, 0.05),
            0.5 + peak * decay + _noise(rng, seg2, 0.1),
            _noise(rng, seg2, 30.0), _noise(rng, seg2, 30.0), _noise(rng, seg2, 30.0),
            label=LABEL_NON_FALL,
        )
        builder.add(*_stationary(rng, seg3, base=(0.0, 0.3, 0.8)), label=LABEL_NON_FALL)

    elif kind == "jolt":
        # sharp jolt that recovers upright (hard negative)
        seg1 = max(1, int(n * 0.4))
        seg2 = max(1, int(n * 0.2))
        seg3 = max(1, n - seg1 - seg2)
        builder.add(*_stationary(rng, seg1), label=LABEL_NON_FALL)
        peak = rng.uniform(1.8, 3.0)
        decay = np.exp(-3.0 * np.arange(seg2) / max(seg2, 1))
        builder.add(
            _noise(rng, seg2, 0.05),
            _noise(rng, seg2, 0.05),
            1.0 + peak * decay + _noise(rng, seg2, 0.1),
            _noise(rng, seg2, 50.0), _noise(rng, seg2, 50.0), _noise(rng, seg2, 50.0),
            label=LABEL_NON_FALL,
        )
        builder.add(*_stationary(rng, seg3), label=LABEL_NON_FALL)

    else:
        builder.add(*_stationary(rng, n), label=LABEL_NON_FALL)


_ADL_KINDS = ["stand", "walk", "turn", "sit_stand", "lie_down", "hard_sit", "jolt"]
_FALL_DIRECTIONS = ["forward", "backward", "left", "right"]


def generate_subject(
    subject_id: int,
    seed: int = 0,
    n_falls: int = 12,
    n_adl: int = 24,
) -> Tuple[List[AccelSample], List[int]]:
    """Generate a single subject's motion stream with per-sample labels.

    The seed is combined with ``subject_id`` so every subject is independent yet
    reproducible.
    """
    rng = np.random.default_rng(seed + subject_id)
    dt = 1.0 / SAMPLE_RATE_HZ
    builder = _StreamBuilder(dt)

    activities: List[Tuple[str, str]] = []
    for _ in range(n_falls):
        activities.append(("fall", rng.choice(_FALL_DIRECTIONS)))
    for _ in range(n_adl):
        activities.append(("adl", rng.choice(_ADL_KINDS)))
    rng.shuffle(activities)

    for kind, arg in activities:
        gap_n = int(rng.uniform(0.5, 1.5) * SAMPLE_RATE_HZ)
        builder.add(*_stationary(rng, gap_n), label=LABEL_NON_FALL)
        if kind == "fall":
            _add_fall(builder, rng, dt, arg)
        else:
            _add_adl(builder, rng, dt, arg)

    return builder.to_samples()


