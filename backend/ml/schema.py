"""Telemetry contract and constants for the JagSi fall-classification model.

This module is the single source of truth for the motion-sample shape, sampling
rate, windowing parameters, label vocabulary, and physical thresholds shared by
data generation, feature extraction, training, and inference.

Units follow the MPU6050 convention used across the project:
    * accelerometer: g (multiples of Earth gravity)
    * gyroscope:     degrees / second
"""

from __future__ import annotations

from dataclasses import dataclass

# --- Sampling ---------------------------------------------------------------
# README: the wearable streams telemetry at 10 Hz for continuous tracking.
SAMPLE_RATE_HZ = 10

# --- Windowing ---------------------------------------------------------------
WINDOW_SECONDS = 3.0
HOP_SECONDS = 1.0

WINDOW_SIZE = int(SAMPLE_RATE_HZ * WINDOW_SECONDS)  # 30 samples
HOP_SIZE = int(SAMPLE_RATE_HZ * HOP_SECONDS)        # 10 samples

# --- Labels -------------------------------------------------------------------
LABEL_NON_FALL = 0
LABEL_FALL = 1

LABEL_NAMES = {LABEL_NON_FALL: "non_fall", LABEL_FALL: "fall"}

# --- Physical thresholds ------------------------------------------------------
FREE_FALL_G_THRESHOLD = 0.5   # SMV below this suggests free fall (g)
IMPACT_G_THRESHOLD = 2.0      # SMV above this suggests an impact (g)
TILT_DEG_THRESHOLD = 30.0     # tilt magnitude suggesting a lying posture (deg)
INACTIVITY_SECONDS = 1.0      # trailing window length checked for inactivity
MPU6050_RANGE_G = 4.0         # typical configured accelerometer range


@dataclass(frozen=True)
class AccelSample:
    """A single motion reading.

    Accelerometer axes are in g; gyroscope axes are in deg/s. ``t`` is elapsed
    seconds since the start of the stream (optional, default 0).
    """

    ax: float
    ay: float
    az: float
    gx: float = 0.0
    gy: float = 0.0
    gz: float = 0.0
    t: float = 0.0


# Ordered, frozen feature vector. ``extract_features`` fills exactly these keys,
# and training/inference index them in exactly this order.
FEATURE_NAMES = [
    # accelerometer magnitude (SMV) statistics
    "smv_mean",
    "smv_max",
    "smv_min",
    "smv_std",
    "smv_peak_to_peak",
    # accelerometer spike / jerk
    "jerk_max",
    "jerk_mean",
    # pitch / roll (tilt)
    "pitch_mean",
    "pitch_range",
    "roll_mean",
    "roll_range",
    "tilt_change",
    # gyroscope magnitude
    "gyro_max",
    "gyro_mean",
    # free fall & impact timing
    "free_fall_min",
    "free_fall_duration",
    "impact_duration",
    # post-impact inactivity
    "post_std",
]
