"""Tests for the synthetic motion generator."""

import math

from ml.features import smv
from ml.schema import IMPACT_G_THRESHOLD, LABEL_FALL, LABEL_NON_FALL
from ml.synth_data import generate_subject


def test_generator_returns_equal_length_streams():
    samples, labels = generate_subject(0, seed=1, n_falls=4, n_adl=8)
    assert len(samples) == len(labels)
    assert len(samples) > 0


def test_generator_is_deterministic():
    a, _ = generate_subject(3, seed=7, n_falls=4, n_adl=8)
    b, _ = generate_subject(3, seed=7, n_falls=4, n_adl=8)
    assert [s.ax for s in a] == [s.ax for s in b]
    assert [s.az for s in a] == [s.az for s in b]


def test_generator_contains_both_classes():
    _, labels = generate_subject(5, seed=9, n_falls=4, n_adl=8)
    assert LABEL_FALL in labels
    assert LABEL_NON_FALL in labels


def test_fall_samples_contain_an_impact_spike():
    samples, labels = generate_subject(1, seed=11, n_falls=6, n_adl=12)
    fall_smv = [
        smv(s.ax, s.ay, s.az) for s, lbl in zip(samples, labels) if lbl == LABEL_FALL
    ]
    assert fall_smv, "expected at least one fall-labelled sample"
    assert max(fall_smv) > IMPACT_G_THRESHOLD
