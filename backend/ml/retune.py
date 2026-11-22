"""Re-tunes the fall decision threshold on labelled recordings (issue #9).

Why not just per-window precision and recall? A recording of one fall is not a
run of "fall" windows. The wearer stands, falls, then lies still, and the 3 s
windows (1 s hop) cover all three phases, so only two or three of them actually
contain the impact. Calling every window in that session a fall would punish the
model for correctly ignoring the standing part.

So falls are scored per session (one supervised fall per recording session) and
everything else per window, the way the caregiver experiences it:

    fall recall      fall sessions with at least one window >= threshold
                     / fall sessions
    false alerts     alerts raised during non-fall sessions, counting a burst of
                     flagged windows as one alert, using the backend's ML cooldown
    alert precision  detected falls / (detected falls + false alerts)
    alerts per hour  false alerts / hours of non-fall recording

The targets from issue #9 (recall >= 0.95, precision >= 0.90) are applied to
fall recall and alert precision.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

# Backend ML cooldown (app/config.py JAGSI_ML_COOLDOWN_S): flagged windows less
# than this far apart become one alert.
DEFAULT_COOLDOWN_WINDOWS = 15
WINDOW_HOP_SECONDS = 1.0

# Below these the numbers are reported but flagged as not enough to trust.
MIN_FALL_SESSIONS = 10
MIN_NON_FALL_MINUTES = 10


@dataclass
class Session:
    name: str
    label: str
    is_fall: bool
    subject: str
    scores: List[float] = field(default_factory=list)  # p(fall) per window, in order


@dataclass
class OperatingPoint:
    threshold: float
    fall_sessions: int
    falls_detected: int
    false_alerts: int
    non_fall_windows: int
    flagged_non_fall_windows: int

    @property
    def recall(self) -> float:
        return self.falls_detected / self.fall_sessions if self.fall_sessions else 0.0

    @property
    def precision(self) -> float:
        denom = self.falls_detected + self.false_alerts
        return self.falls_detected / denom if denom else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p + r else 0.0

    @property
    def false_alerts_per_hour(self) -> float:
        hours = self.non_fall_windows * WINDOW_HOP_SECONDS / 3600
        return self.false_alerts / hours if hours else 0.0

    def as_dict(self) -> Dict[str, float]:
        return {
            "threshold": round(self.threshold, 3),
            "fall_recall": round(self.recall, 3),
            "alert_precision": round(self.precision, 3),
            "f1": round(self.f1, 3),
            "falls_detected": self.falls_detected,
            "fall_sessions": self.fall_sessions,
            "false_alerts": self.false_alerts,
            "false_alerts_per_hour": round(self.false_alerts_per_hour, 2),
            "flagged_non_fall_windows": self.flagged_non_fall_windows,
            "non_fall_windows": self.non_fall_windows,
        }


# ---------------------------------------------------------------------------
# Loading and scoring
# ---------------------------------------------------------------------------
def load_recordings(directory: Path | str) -> Dict[str, List[dict]]:
    """Reads every *.jsonl written by app.recorder, grouped by session."""
    sessions: Dict[str, List[dict]] = defaultdict(list)
    for path in sorted(Path(directory).glob("*.jsonl")):
        with open(path, encoding="utf-8") as fh:
            for line_no, line in enumerate(fh, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"{path.name}:{line_no} is not valid JSON") from exc
                sessions[rec["session"]].append(rec)
    return dict(sessions)


def score_sessions(raw: Dict[str, List[dict]], classifier, parse_window) -> tuple[List[Session], Dict[str, int]]:
    """Scores each recorded window with the classifier.

    ``parse_window`` is the backend's own validator, so a window the live
    pipeline would refuse is not used to tune the threshold either.
    """
    from ml.schema import LABEL_FALL

    fall_col = list(classifier.pipeline.classes_).index(LABEL_FALL)
    out: List[Session] = []
    rejected: Dict[str, int] = defaultdict(int)
    for name, records in raw.items():
        first = records[0]
        s = Session(name=name, label=first["label"], is_fall=bool(first["is_fall"]), subject=first["subject"])
        for rec in records:
            try:
                samples = parse_window(rec["window"])
            except Exception as exc:  # WindowRejected, KeyError
                rejected[type(exc).__name__ + ": " + str(exc).split(",")[0]] += 1
                continue
            _, proba = classifier.predict_proba(samples)
            s.scores.append(float(proba[fall_col]))
        if s.scores:
            out.append(s)
    return out, dict(rejected)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
def count_alerts(scores: Sequence[float], threshold: float, cooldown_windows: int) -> int:
    """Alerts the backend would raise: flagged windows, minus those in cooldown."""
    alerts, last = 0, None
    for i, p in enumerate(scores):
        if p >= threshold and (last is None or i - last >= cooldown_windows):
            alerts += 1
            last = i
    return alerts


def evaluate(sessions: Iterable[Session], threshold: float, cooldown_windows: int = DEFAULT_COOLDOWN_WINDOWS) -> OperatingPoint:
    falls = detected = false_alerts = nf_windows = nf_flagged = 0
    for s in sessions:
        if s.is_fall:
            falls += 1
            if any(p >= threshold for p in s.scores):
                detected += 1
        else:
            nf_windows += len(s.scores)
            nf_flagged += sum(1 for p in s.scores if p >= threshold)
            false_alerts += count_alerts(s.scores, threshold, cooldown_windows)
    return OperatingPoint(threshold, falls, detected, false_alerts, nf_windows, nf_flagged)


def sweep(sessions: List[Session], thresholds: Optional[Sequence[float]] = None, cooldown_windows: int = DEFAULT_COOLDOWN_WINDOWS) -> List[OperatingPoint]:
    if thresholds is None:
        thresholds = [round(0.05 + 0.01 * i, 2) for i in range(91)]   # 0.05 .. 0.95
    return [evaluate(sessions, t, cooldown_windows) for t in thresholds]


def choose_threshold(points: List[OperatingPoint], min_recall: float, min_precision: float) -> tuple[OperatingPoint, str]:
    """Picks the operating point, weighting precision as much as recall.

    If several thresholds meet both targets, the middle of the longest run of
    passing thresholds is chosen: a value in the middle of a safe band survives
    small changes in how people move better than one at the edge of it.
    Otherwise the best F1 among those meeting the recall target, and failing
    that the best F1 overall, with the reason stated.
    """
    passing = [p.recall >= min_recall and p.precision >= min_precision for p in points]
    best_run, run_start = (0, -1, -1), None
    for i, ok in enumerate(passing + [False]):
        if ok and run_start is None:
            run_start = i
        elif not ok and run_start is not None:
            length = i - run_start
            if length > best_run[0]:
                best_run = (length, run_start, i - 1)
            run_start = None
    if best_run[0] > 0:
        _, lo, hi = best_run
        return points[(lo + hi) // 2], (
            f"meets both targets for thresholds {points[lo].threshold:.2f} to "
            f"{points[hi].threshold:.2f}; middle of that range chosen"
        )
    meeting_recall = [p for p in points if p.recall >= min_recall]
    if meeting_recall:
        best = max(meeting_recall, key=lambda p: (p.f1, p.threshold))
        return best, "no threshold meets the precision target; best F1 that keeps recall"
    best = max(points, key=lambda p: (p.f1, p.threshold))
    return best, "no threshold meets the recall target; best F1 overall. Do not deploy."


def per_activity(sessions: Iterable[Session], threshold: float, cooldown_windows: int = DEFAULT_COOLDOWN_WINDOWS) -> List[Dict[str, object]]:
    by_label: Dict[str, List[Session]] = defaultdict(list)
    for s in sessions:
        by_label[s.label].append(s)
    rows = []
    for label in sorted(by_label, key=lambda l: (l.startswith("fall"), l)):
        group = by_label[label]
        windows = sum(len(s.scores) for s in group)
        flagged = sum(1 for s in group for p in s.scores if p >= threshold)
        row: Dict[str, object] = {
            "activity": label,
            "sessions": len(group),
            "windows": windows,
            "flagged_windows": flagged,
            "flagged_rate": round(flagged / windows, 3) if windows else 0.0,
            "mean_p_fall": round(sum(p for s in group for p in s.scores) / windows, 3) if windows else 0.0,
        }
        if group[0].is_fall:
            row["sessions_detected"] = sum(1 for s in group if any(p >= threshold for p in s.scores))
        else:
            row["alerts"] = sum(count_alerts(s.scores, threshold, cooldown_windows) for s in group)
        rows.append(row)
    return rows


def sufficiency_warnings(sessions: List[Session]) -> List[str]:
    warnings = []
    falls = sum(1 for s in sessions if s.is_fall)
    if falls < MIN_FALL_SESSIONS:
        warnings.append(f"only {falls} fall sessions (want at least {MIN_FALL_SESSIONS}); recall is not reliable yet")
    minutes: Dict[str, float] = defaultdict(float)
    for s in sessions:
        if not s.is_fall:
            minutes[s.label] += len(s.scores) * WINDOW_HOP_SECONDS / 60
    total = sum(minutes.values())
    if total < MIN_NON_FALL_MINUTES:
        warnings.append(
            f"only {total:.1f} minutes of non-fall movement (want at least {MIN_NON_FALL_MINUTES}); "
            "false alerts per hour is not reliable yet"
        )
    for needed in ("walking", "sit_down_hard", "stairs"):
        if needed not in minutes:
            warnings.append(f"no '{needed}' recordings: the hardest non-falls are missing")
    subjects = {s.subject for s in sessions}
    if len(subjects) < 2:
        warnings.append("all recordings are from one person; the threshold may not transfer to others")
    return warnings
