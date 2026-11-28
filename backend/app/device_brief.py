"""Combine verified lab rows and device-scoped telemetry through the local LLM."""
import logging
import subprocess
from .brief_worker import infer_pattern, lock
from datetime import datetime, timezone

from .ai_summary import build_context, _parse
from .evidence_summary import daily_brief, summarize
from .local_brief import MODEL_ID


def device_brief(store, device_id, wearer, rows, lab_date):
    rows = [{**r, "unit": r["unit"].strip() or "(satuan belum dikonfirmasi)"} for r in rows]
    ctx = build_context(store, device_id, wearer)
    latest = ctx["latest"] or {}
    when = _parse(latest.get("received_at"))
    stale = bool(latest and (not when or (datetime.now(timezone.utc) - when).total_seconds() >= 10))
    readings = [(title, latest[key], unit) for key, title, unit in (
        ("heart_rate", "detak jantung", "bpm"), ("spo2", "SpO2", "%"),
        ("body_temperature", "suhu", "°C")) if latest.get(key) is not None]
    alert = any(a["status"] != "acknowledged" for a in ctx["alerts_24h"])
    observations = dict(lab_date=lab_date, reviewed_rows=rows, readings=readings,
                        watch_time=latest.get("received_at") if when else None, simulated=bool(latest.get("simulated")),
                        stale=stale, active_alert=alert)
    watch = "kosong" if not readings or not when else "tertunda" if stale else "simulasi" if latest["simulated"] else "aktual"
    high = any(r["label"].strip().casefold() == "ldl cholesterol" and
               r["flag"].strip().lower() in ("h", "high", "tinggi") for r in rows)
    state = dict(watch=watch, alert=alert, ldl_high=high)
    try:
        with lock:
            pattern = infer_pattern(**state)
        text = pattern.replace("NAME", wearer).replace("FACTS", summarize(**observations))
        return {"text": text, "model": MODEL_ID, "source": "local_llm"}
    except (OSError, subprocess.SubprocessError, KeyError, ValueError) as exc:
        logging.getLogger("jagsi.ai").warning("Daily brief used local rules (%s)", type(exc).__name__)
        return {"text": daily_brief(wearer=wearer, **observations), "model": "JagSi rules", "source": "rules"}