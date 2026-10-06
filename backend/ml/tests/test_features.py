"""Unit tests for motion feature extraction and windowing."""

import math

from ml.features import (
    extract_features,
    gyro_magnitude,
    pitch_degrees,
    roll_degrees,
    sliding_windows,
    smv,
)
from ml.schema import AccelSample, FEATURE_NAMES, WINDOW_SIZE


def _window(*samples: AccelSample) -> list[AccelSample]:
    return list(samples)


def test_smv_of_upright_is_one_g():
    assert math.isclose(smv(0.0, 0.0, 1.0), 1.0)


def test_pitch_and_roll_of_upright_are_zero():
    assert math.isclose(pitch_degrees(0.0, 1.0), 0.0)
    assert math.isclose(roll_degrees(0.0, 0.0, 1.0), 0.0)


def test_roll_of_prone_is_large():
    # face-down: ax = -0.9 g, az ~ 0.15 g -> roll near +80 degrees
    roll = roll_degrees(-0.9, 0.0, 0.15)
    assert roll > 70.0


def test_gyro_magnitude():
    assert math.isclose(gyro_magnitude(3.0, 4.0, 0.0), 5.0)


def test_extract_features_returns_all_keys():
    upright = [AccelSample(0.0, 0.0, 1.0) for _ in range(WINDOW_SIZE)]
    features = extract_features(upright)
    assert list(features.keys()) == FEATURE_NAMES


def test_extract_features_upright_has_unit_smv_and_no_tilt():
    upright = [AccelSample(0.0, 0.0, 1.0) for _ in range(WINDOW_SIZE)]
    features = extract_features(upright)
    assert math.isclose(features["smv_mean"], 1.0, abs_tol=1e-6)
    assert math.isclose(features["pitch_mean"], 0.0, abs_tol=1e-6)
    assert math.isclose(features["roll_mean"], 0.0, abs_tol=1e-6)
    assert features["tilt_change"] < 1.0


def test_extract_features_empty_window_is_all_zero():
    features = extract_features([])
    assert features == {name: 0.0 for name in FEATURE_NAMES}


def test_sliding_windows_counts_and_shapes():
    samples = [AccelSample(0.0, 0.0, 1.0) for _ in range(100)]
    windows = sliding_windows(samples, window_size=30, hop_size=10)
    assert len(windows) == 8  # starts at 0,10,...,70
    assert all(len(w) == 30 for w in windows)


def test_extract_features_detects_fall_signature():
    # hand-built fall-like window: upright -> dip -> impact -> prone
    samples = []
    samples += [AccelSample(0.0, 0.0, 1.0) for _ in range(10)]      # upright
    samples += [AccelSample(0.0, 0.0, 0.2) for _ in range(5)]       # free fall
    samples += [AccelSample(0.0, 0.0, 3.0) for _ in range(5)]       # impact spike
    samples += [AccelSample(-0.9, 0.0, 0.15) for _ in range(10)]    # prone
    features = extract_features(samples)
    assert features["smv_max"] > 2.0
    assert features["tilt_change"] > 30.0
    assert features["post_std"] < 0.5
