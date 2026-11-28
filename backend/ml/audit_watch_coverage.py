"""Summarize local input coverage without exporting wearer IDs or individual values."""
import json
import sqlite3
from pathlib import Path
from statistics import median
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]


def main():
    db = ROOT / "backend/data/jagsi.db"
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("""SELECT device_id, received_at, simulated, heart_rate, spo2,
            body_temperature FROM telemetry_data ORDER BY device_id, received_at, telemetry_id""").fetchall()
    previous = {}
    gaps = []
    invalid = 0
    for row in rows:
        try:
            when = datetime.strptime(row["received_at"], "%Y-%m-%dT%H:%M:%SZ")
        except (TypeError, ValueError):
            invalid += 1
            continue
        device = row["device_id"]
        if device in previous:
            gaps.append((when - previous[device]).total_seconds())
        previous[device] = when
    report = dict(rows=len(rows), devices=len({r["device_id"] for r in rows}),
                  simulated_rows=sum(r["simulated"] == 1 for r in rows),
                  present={k: sum(r[k] is not None for r in rows)
                           for k in ("heart_rate", "spo2", "body_temperature")},
                  invalid_receive_times=invalid, consecutive_intervals=len(gaps),
                  median_interval_seconds=median(gaps) if gaps else None,
                  max_interval_seconds=max(gaps, default=None),
                  intervals_at_least_10s=sum(x >= 10 for x in gaps))
    print(json.dumps(report, indent=2))
    (ROOT / "docs/evidence/watch-input-coverage.json").write_text(json.dumps(report, indent=2)+"\n")


if __name__ == "__main__":
    main()
