"""Labelled recording of real motion windows, for re-tuning the fall threshold.

Week 6 showed the classifier's stored threshold (0.11) flags ordinary walking as a
fall, but that finding came from synthetic windows, so it cannot say what the
right threshold is. The only honest answer comes from the physical MPU6050.

How a session works (issue #9):

    1. POST /api/recording/start {"label": "walking", "subject": "s01"}
    2. the wearer walks for a minute; every motion window the watch publishes is
       appended to data/recordings/<session>.jsonl, untouched
    3. POST /api/recording/stop
    4. repeat per activity, then run scripts/retune_threshold.py on the folder

Labels starting with ``fall`` count as falls (fall_forward, fall_backward,
fall_side). Everything else is a non-fall. Falls must be supervised and onto a
mattress; see docs/recording-protocol.md.
"""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# The activities in the recording protocol. Others are allowed as long as the
# name is a safe file-name slug, but these are what the re-tune report groups by.
SUGGESTED_LABELS = [
    "still",
    "walking",
    "stairs",
    "sit_to_stand",
    "sit_down_hard",
    "lie_down",
    "fall_forward",
    "fall_backward",
    "fall_side",
]

_SLUG = re.compile(r"^[a-z0-9_]{1,40}$")


def is_fall_label(label: str) -> bool:
    return label.startswith("fall")


class RecordingError(ValueError):
    pass


class MotionRecorder:
    """Appends raw motion windows to a JSONL file while a session is open."""

    def __init__(self, directory: str | Path) -> None:
        self.directory = Path(directory)
        self._lock = threading.Lock()
        self._session: Optional[Dict[str, Any]] = None

    @property
    def active(self) -> bool:
        return self._session is not None

    def start(self, label: str, subject: str, device_id: Optional[str] = None, note: str = "") -> Dict[str, Any]:
        label = (label or "").strip().lower()
        subject = (subject or "").strip().lower()
        if not _SLUG.match(label):
            raise RecordingError("label must be lowercase letters, digits or _ (e.g. walking, fall_side)")
        if not _SLUG.match(subject):
            raise RecordingError("subject must be lowercase letters, digits or _ (e.g. s01)")
        with self._lock:
            if self._session is not None:
                raise RecordingError(f"session {self._session['session']} is still open, stop it first")
            started = datetime.now(timezone.utc)
            base = f"{started.strftime('%Y%m%dT%H%M%SZ')}_{subject}_{label}"
            self.directory.mkdir(parents=True, exist_ok=True)
            # Two sessions started in the same second must not share a file:
            # each fall recording has to stay its own session.
            session, n = base, 1
            while (self.directory / f"{session}.jsonl").exists():
                n += 1
                session = f"{base}_{n}"
            self._session = {
                "session": session,
                "label": label,
                "is_fall": is_fall_label(label),
                "subject": subject,
                "device_id": device_id,
                "note": note,
                "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "windows": 0,
                "path": str(self.directory / f"{session}.jsonl"),
            }
            Path(self._session["path"]).touch()
            return dict(self._session)

    def stop(self) -> Dict[str, Any]:
        with self._lock:
            if self._session is None:
                raise RecordingError("no recording session is open")
            done = dict(self._session)
            self._session = None
        done["stopped_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        return done

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {"active": self._session is not None, "session": dict(self._session) if self._session else None}

    def record(self, msg: Dict[str, Any]) -> bool:
        """Stores one window. Returns False when it is not for this session."""
        with self._lock:
            s = self._session
            if s is None:
                return False
            if s["device_id"] and msg.get("device_id") != s["device_id"]:
                return False
            line = {
                "session": s["session"],
                "label": s["label"],
                "is_fall": s["is_fall"],
                "subject": s["subject"],
                "received_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "window": msg,
            }
            with open(s["path"], "a", encoding="utf-8") as fh:
                fh.write(json.dumps(line, separators=(",", ":")) + "\n")
            s["windows"] += 1
            return True
