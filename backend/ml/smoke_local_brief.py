"""Smoke-test actual LoRA inference with a disposable watch and MCU record."""
import sys
import tempfile
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo / "backend"))
from unittest.mock import patch
from app.main import BriefInput, daily_health_brief
from app.store import Store


def main():
    with tempfile.TemporaryDirectory(dir=repo / "backend/data/llm/tmp") as tmp:
        store = Store(Path(tmp) / "demo.db")
        store.insert_telemetry(dict(device_id="smoke", seq=1, ts=None, uptime_ms=1,
            heart_rate=78, spo2=97, body_temperature=36.6, accel=dict(x=0,y=0,z=1),
            accel_peak_g=1, battery_level=87, sim=True))
        labs = [dict(label="LDL cholesterol", value="142", unit="mg/dL", flag="H")]
        with patch("app.main.store", store):
            result = daily_health_brief("smoke", BriefInput(reviewed_rows=labs, lab_date="2026-05-02"))
        print(result["source"], result["model"], result["text"], sep="\n", flush=True)
        assert result["source"] == "local_llm"
        assert all(s in result["text"] for s in ("142 mg/dL", "78", "Simulasi", "SpO2"))


if __name__ == "__main__":
    main()
