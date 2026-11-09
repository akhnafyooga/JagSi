#!/usr/bin/env python3
"""Chooses a new fall decision threshold from real, labelled recordings (issue #9).

    cd backend
    python3 scripts/retune_threshold.py                       # report only
    python3 scripts/retune_threshold.py --write-artifact ml/artifacts/fall_clf_retuned.joblib
    python3 scripts/retune_threshold.py --json docs/retune-result.json

Recordings come from the backend's recording endpoints (see
docs/recording-protocol.md) and live in data/recordings/*.jsonl.

It never overwrites the deployed artifact. ``--write-artifact`` saves a copy
with the new threshold and the evidence in its metadata; the model owner reviews
the report, then swaps the file or sets JAGSI_FALL_THRESHOLD.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
warnings.filterwarnings("ignore")

from app.bridge import parse_window  # noqa: E402
from app.config import settings  # noqa: E402
from ml.inference import FallClassifier  # noqa: E402
from ml.retune import (  # noqa: E402
    DEFAULT_COOLDOWN_WINDOWS,
    choose_threshold,
    evaluate,
    load_recordings,
    per_activity,
    score_sessions,
    sufficiency_warnings,
    sweep,
)


def table(rows, columns):
    widths = {c: max(len(c), *(len(str(r.get(c, ""))) for r in rows)) for c in columns}
    line = "  ".join(c.ljust(widths[c]) for c in columns)
    out = [line, "-" * len(line)]
    for r in rows:
        out.append("  ".join(str(r.get(c, "")).ljust(widths[c]) for c in columns))
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recordings", type=Path, default=Path(settings.recordings_dir))
    ap.add_argument("--model", type=Path, default=Path(settings.model_path))
    ap.add_argument("--min-recall", type=float, default=0.95)
    ap.add_argument("--min-precision", type=float, default=0.90)
    ap.add_argument("--cooldown-windows", type=int, default=DEFAULT_COOLDOWN_WINDOWS)
    ap.add_argument("--write-artifact", type=Path, help="save a COPY of the model with the chosen threshold")
    ap.add_argument("--json", type=Path, help="write the full result as JSON")
    args = ap.parse_args(argv)

    raw = load_recordings(args.recordings)
    if not raw:
        print(f"No recordings in {args.recordings}. See docs/recording-protocol.md.", file=sys.stderr)
        return 2

    clf = FallClassifier.load(str(args.model))
    stored = clf.threshold
    sessions, rejected = score_sessions(raw, clf, parse_window)
    if not sessions:
        print("Every recorded window was rejected by the window contract:", rejected, file=sys.stderr)
        return 2

    points = sweep(sessions, cooldown_windows=args.cooldown_windows)
    chosen, why = choose_threshold(points, args.min_recall, args.min_precision)
    at_stored = evaluate(sessions, stored, args.cooldown_windows)
    warn = sufficiency_warnings(sessions)

    print(f"\nModel:       {args.model}")
    print(f"Recordings:  {args.recordings}  ({len(sessions)} sessions, "
          f"{sum(len(s.scores) for s in sessions)} windows)")
    if rejected:
        print(f"Rejected:    {sum(rejected.values())} windows {rejected}")
    print(f"Targets:     fall recall >= {args.min_recall}, alert precision >= {args.min_precision}\n")

    cols = ["threshold", "fall_recall", "alert_precision", "false_alerts_per_hour", "falls_detected", "fall_sessions", "false_alerts"]
    print(table([at_stored.as_dict() | {"threshold": f"{stored:.2f} (stored)"}, chosen.as_dict() | {"threshold": f"{chosen.threshold:.2f} (chosen)"}], cols))
    print(f"\nChoice: {why}\n")
    print("Per activity at the chosen threshold:")
    acts = per_activity(sessions, chosen.threshold, args.cooldown_windows)
    print(table(acts, ["activity", "sessions", "windows", "flagged_windows", "flagged_rate", "mean_p_fall", "alerts", "sessions_detected"]))
    if warn:
        print("\nNot enough data to trust this yet:")
        for w in warn:
            print(f"  - {w}")

    result = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model": str(args.model),
        "stored_threshold": stored,
        "chosen": chosen.as_dict(),
        "at_stored": at_stored.as_dict(),
        "reason": why,
        "per_activity": acts,
        "sweep": [p.as_dict() for p in points],
        "warnings": warn,
        "rejected_windows": rejected,
        "sessions": len(sessions),
        "subjects": sorted({s.subject for s in sessions}),
    }
    if args.json:
        args.json.write_text(json.dumps(result, indent=2))
        print(f"\nWrote {args.json}")

    if args.write_artifact:
        if args.write_artifact.resolve() == args.model.resolve():
            print("Refusing to overwrite the deployed artifact; pick another path.", file=sys.stderr)
            return 2
        clf.threshold = chosen.threshold
        clf.metadata = {
            **clf.metadata,
            "retuned": {
                "at": result["generated_at"],
                "previous_threshold": stored,
                "operating_point": chosen.as_dict(),
                "sessions": len(sessions),
                "subjects": result["subjects"],
                "warnings": warn,
            },
        }
        clf.save(str(args.write_artifact))
        print(f"Wrote {args.write_artifact} with threshold {chosen.threshold:.2f}")

    meets = chosen.recall >= args.min_recall and chosen.precision >= args.min_precision
    return 0 if meets and not warn else 1


if __name__ == "__main__":
    raise SystemExit(main())
