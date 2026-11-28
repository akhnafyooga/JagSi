"""Reproducible evidence-contract benchmark. Uses the actual trained worker by default."""
import itertools
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from pydantic import ValidationError
from app.main import BriefInput, daily_health_brief
from app.brief_worker import infer_pattern
from app.store import Store

NOW = "2026-11-28T08:30:00Z"
OLD = "2026-11-28T08:29:50Z"


class Clock(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 28, 8, 30, tzinfo=timezone.utc)


def lab(label, value, unit="", flag=""):
    return dict(label=label, value=value, unit=unit, flag=flag)


LABS = [
    ([], False),
    ([lab("LDL cholesterol", "142", "mg/dL", "H")], True),
    ([lab("ldl cholesterol", "3,8", "mmol/L", " tinggi ")], True),
    ([lab("LDL cholesterol", "<82.5", "mg/dL")], False),
    ([lab("Hemoglobin", "10.1", "g/dL", "L")], False),
    ([lab("Creatinine", "1.04")], False),
    ([lab("HbA1c", "6.1", "%", "H"), lab("LDL cholesterol", "145", "mg/dL", "HIGH")], True),
]
WATCH = {
    "missing": None,
    "fresh": (NOW, False, 78, 97.5),
    "simulated": (NOW, True, 153, 96.1),
    "partial": (NOW, False, None, 98.2),
    "boundary": (OLD, False, 87, 95.4),
    "stale_sim": (OLD, True, 98, None),
    "invalid_time": ("unknown", False, 88, 99),
}


def run():
    records = []
    with tempfile.TemporaryDirectory(dir=ROOT / "backend/data/llm/tmp") as folder:
        store = Store(Path(folder) / "bench.db")
        with patch("app.main.store", store), patch("app.device_brief.datetime", Clock), patch("app.ai_summary.datetime", Clock):
            for i, (watch, alert, (rows, high), date) in enumerate(itertools.product(
                    WATCH, ("none", "open", "acknowledged"), LABS, (None, "2026-05-02"))):
                device = f"bench-{i}"
                sample = WATCH[watch]
                if sample:
                    stamp, sim, hr, oxygen = sample
                    with patch("app.store.utcnow", return_value=stamp):
                        store.insert_telemetry(dict(device_id=device, sim=sim, heart_rate=hr, spo2=oxygen))
                if alert != "none":
                    with patch("app.store.utcnow", return_value=NOW):
                        store.insert_alert(alert_id=device, device_id=device, alert_type="sos", source="bench")
                    if alert == "acknowledged":
                        store.acknowledge_alert(device)
                body = BriefInput(reviewed_rows=rows, lab_date=date)
                output = daily_health_brief(device, body)
                repeat = daily_health_brief(device, body)
                text = output["text"]
                available = watch not in ("missing", "invalid_time")
                checks = {
                    "actual_adapter": output["source"] == "local_llm",
                    "repeat_identical": output == repeat,
                    "watch_available": ("Belum ada pembacaan jam" not in text) == available,
                    "simulated": ("Simulasi jam" in text) == (watch in ("simulated", "stale_sim")),
                    "delayed": ("Pembaruan jam tertunda" in text) == (watch in ("boundary", "stale_sim", "invalid_time")),
                    "lab_available": ("Belum ada hasil MCU" not in text) == bool(rows),
                    "date": ("2026-05-02" in text) == bool(rows and date),
                    "unknown_date": ("tanggal belum terkonfirmasi" in text) == bool(rows and not date),
                    "lab_evidence": all(f"{r['label']} {r['value']} {r['unit'] or '(satuan belum dikonfirmasi)'}" in text for r in rows),
                    "alert_priority": ("Langkah sekarang" in text) == (alert == "open"),
                    "food_constrained": ("pepes ikan" in text) == (high and alert != "open"),
                    "bullet_count": len(text.splitlines()) == (2 if alert == "open" else 3),
                }
                if sample:
                    for label, value, unit in (("detak jantung", hr, "bpm"), ("SpO2", oxygen, "%")):
                        checks[label] = (f"{label} " in text) == bool(available and value is not None)
                        if available and value is not None:
                            checks[label] &= f"{label} {value}" in text and unit in text
                records.append(dict(case=device, watch=watch, sample=sample, alert=alert, request=body.model_dump(mode="json"),
                                    output=output, repeat_output=repeat if repeat != output else None, checks=checks))
    invalid = [
        {"reviewed_rows": [lab(" ", "1")]}, {"reviewed_rows": [lab("LDL cholesterol", " ")]},
        {"reviewed_rows": [lab("A\nB", "1")]}, {"lab_date": "2026-02-30"},
        {"reviewed_rows": [lab("X", "1")] * 101}, {"reviewed_rows": [lab("X", "1"*49)]},
    ]
    for payload in invalid:
        try:
            BriefInput.model_validate(payload)
            rejected = False
        except ValidationError:
            rejected = True
        records.append(dict(case=f"invalid-{len(records)}", request=payload, checks={"rejected": rejected}))
    target = ROOT / "docs/evidence/daily-brief-input-quality.jsonl"
    target.write_text("".join(json.dumps(r, ensure_ascii=False)+"\n" for r in records), encoding="utf-8")
    failures = [(r["case"], k) for r in records for k, ok in r["checks"].items() if not ok]
    print(len(records), "cases,", sum(len(r["checks"]) for r in records), "checks,", len(failures), "failures", infer_pattern.cache_info())
    print(failures[:12])
    return bool(failures)


if __name__ == "__main__":
    sys.exit(run())
