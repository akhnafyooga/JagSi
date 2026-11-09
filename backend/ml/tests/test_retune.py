"""Threshold re-tuning on labelled recordings (issue #9)."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

from ml.retune import (
    Session,
    choose_threshold,
    count_alerts,
    evaluate,
    per_activity,
    sufficiency_warnings,
    sweep,
)

BACKEND = Path(__file__).resolve().parents[2]
TOOLS = BACKEND.parent / "tools"


def test_cooldown_turns_a_burst_into_one_alert():
    scores = [0.9] * 10 + [0.0] * 10 + [0.9]          # flagged again 20 windows later
    assert count_alerts(scores, 0.5, cooldown_windows=15) == 2
    assert count_alerts(scores, 0.5, cooldown_windows=1) == 11
    assert count_alerts(scores, 0.95, cooldown_windows=15) == 0


def test_fall_is_scored_per_session_not_per_window():
    """Only the impact windows of a fall recording score high; that is a hit."""
    fall = Session("f1", "fall_side", True, "s01", scores=[0.05] * 8 + [0.97, 0.9] + [0.1] * 5)
    walk = Session("w1", "walking", False, "s01", scores=[0.15] * 60)
    point = evaluate([fall, walk], threshold=0.5)
    assert point.recall == 1.0 and point.false_alerts == 0 and point.precision == 1.0

    low = evaluate([fall, walk], threshold=0.11)
    assert low.false_alerts == 4                       # 60 windows, one alert per 15
    assert low.precision == pytest.approx(1 / 5)
    assert low.false_alerts_per_hour == pytest.approx(4 / (60 / 3600))


def test_choose_middle_of_passing_band():
    sessions = [
        Session("f", "fall_side", True, "s01", scores=[0.9]),
        Session("w", "walking", False, "s01", scores=[0.3] * 30),
    ]
    points = sweep(sessions, thresholds=[0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.95])
    chosen, why = choose_threshold(points, 0.95, 0.90)
    # 0.2 and 0.3 flag walking; 0.4..0.7 pass; 0.95 misses the fall.
    assert chosen.threshold == 0.5
    assert "0.40 to 0.70" in why


def test_no_passing_threshold_is_reported_honestly():
    sessions = [
        Session("f", "fall_side", True, "s01", scores=[0.4]),
        Session("w", "walking", False, "s01", scores=[0.6] * 30),
    ]
    chosen, why = choose_threshold(sweep(sessions), 0.95, 0.90)
    assert "precision" in why or "recall" in why


def test_per_activity_rows_and_warnings():
    sessions = [
        Session("f", "fall_side", True, "s01", scores=[0.9]),
        Session("w", "walking", False, "s01", scores=[0.1] * 10),
    ]
    rows = {r["activity"]: r for r in per_activity(sessions, 0.5)}
    assert rows["fall_side"]["sessions_detected"] == 1
    assert rows["walking"]["alerts"] == 0
    warnings = sufficiency_warnings(sessions)
    assert any("fall sessions" in w for w in warnings)
    assert any("one person" in w for w in warnings)


# -- end to end with the real model and the real recorder -------------------
@pytest.fixture
def recordings(tmp_path):
    sys.path.insert(0, str(TOOLS))
    from fake_device import fall_samples, still_sample, walking_sample  # noqa: E402

    from app.recorder import MotionRecorder

    random.seed(3)
    rec = MotionRecorder(tmp_path)

    def window(rows, seq):
        return {"device_id": "w", "seq": seq, "sample_rate_hz": 10, "window_size": 30, "dropped": 0, "s": rows}

    for subject in ("s01", "s02"):
        rec.start("walking", subject)
        for i in range(60):
            rec.record(window([walking_sample((i + k / 10) * 1.0) for k in range(30)], i))
        rec.stop()
        for n in range(6):
            rec.start("fall_side", subject)
            # stand, fall, then lie still: the fall is in only a few windows
            stream = [still_sample(k / 10) for k in range(40)] + fall_samples() + [still_sample(k / 10) for k in range(30)]
            for i in range(0, len(stream) - 30 + 1, 10):
                rec.record(window(stream[i:i + 30], i))
            rec.stop()
    # one broken window, which the live pipeline would refuse too
    rec.start("still", "s01")
    rec.record({**window([[0, 0, 1, 0, 0, 0]] * 30, 0), "dropped": 2})
    rec.stop()
    return tmp_path


def test_retune_script_end_to_end(recordings, tmp_path, capsys):
    sys.path.insert(0, str(BACKEND / "scripts"))
    import retune_threshold

    out_json = tmp_path / "result.json"
    out_model = tmp_path / "retuned.joblib"
    retune_threshold.main(
        ["--recordings", str(recordings), "--json", str(out_json), "--write-artifact", str(out_model)]
    )
    result = json.loads(out_json.read_text())
    assert result["stored_threshold"] == pytest.approx(0.11, abs=0.01)
    # the stored threshold raises false alerts on walking; the chosen one does not
    assert result["at_stored"]["false_alerts"] > 0
    assert result["chosen"]["false_alerts"] == 0
    assert result["chosen"]["fall_recall"] == 1.0
    assert result["chosen"]["threshold"] > result["stored_threshold"]
    assert sum(result["rejected_windows"].values()) == 1

    from ml.inference import FallClassifier

    retuned = FallClassifier.load(str(out_model))
    assert retuned.threshold == result["chosen"]["threshold"]
    assert retuned.metadata["retuned"]["previous_threshold"] == result["stored_threshold"]
    assert "Per activity" in capsys.readouterr().out


def test_refuses_to_overwrite_deployed_model(recordings):
    sys.path.insert(0, str(BACKEND / "scripts"))
    import retune_threshold
    from app.config import settings

    assert retune_threshold.main(["--recordings", str(recordings), "--write-artifact", settings.model_path]) == 2
