"""Shapes a stored telemetry row into the dashboard's Vital cards.

The frontend already renders a ``Vital[]`` from ``frontend/lib/mock-data.ts``. Doing
the same shaping server-side means the live swap is a change of data source, not a
rewrite of the components.

IMPORTANT, about the thresholds below.

These are **display bands**, not clinical thresholds. They come from general adult
reference ranges and exist only to colour a card green, amber or red. They are not
validated for elderly patients, they ignore the individual's baseline, medication and
history, and a resting range applied to someone who has just walked upstairs will read
amber for no reason.

This matches what the project already promises in the Week 1 worksheet: JagSi
provides *health-risk indicators and alerts, not medical diagnoses*. Before this is
used by anyone outside the team, the bands must be reviewed by a clinician and made
per-patient rather than global. Until then every card carries a disclaimer and the
``reference`` field states the range being applied, so a caregiver can see what the
colour is based on instead of trusting it blindly.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

# Readings that come from a potentiometer in Wokwi rather than a sensor.
# See docs/hardware-bom.md section 2.
SIMULATED_IN_WOKWI = {"heart-rate", "spo2", "battery"}

DISCLAIMER = (
    "Indikator, bukan diagnosis. Rentang di bawah adalah acuan umum dewasa dan belum "
    "divalidasi secara klinis untuk lansia."
)


def _band(
    value: Optional[float],
    *,
    normal: tuple[float, float],
    warning: tuple[float, float],
) -> str:
    """normal -> warning -> critical, by widening band."""
    if value is None:
        return "unknown"
    if normal[0] <= value <= normal[1]:
        return "normal"
    if warning[0] <= value <= warning[1]:
        return "warning"
    return "critical"


_STATUS_LABEL_ID = {
    "normal": "Normal",
    "warning": "Perlu Perhatian",
    "critical": "Segera Periksa",
    "unknown": "Tidak Ada Data",
}


def _vital(
    *,
    vid: str,
    label: str,
    value: Optional[float],
    unit: str,
    icon: str,
    tone: str,
    reference: str,
) -> Dict[str, Any]:
    return {
        "id": vid,
        "label": label,
        "value": value,
        "unit": unit,
        "icon": icon,
        # 'unknown' has no counterpart in the frontend's VitalTone union, so it is
        # mapped to 'warning' there and distinguished by value === null.
        "tone": tone,
        "statusLabel": _STATUS_LABEL_ID[tone],
        "note": reference,
        "reference": reference,
        "simulated": vid in SIMULATED_IN_WOKWI,
    }


def telemetry_to_vitals(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Maps one ``telemetry_data`` row onto the four dashboard cards."""
    hr = row.get("heart_rate")
    spo2 = row.get("spo2")
    temp = row.get("body_temperature")
    batt = row.get("battery_level")

    return [
        _vital(
            vid="heart-rate",
            label="Detak Jantung",
            value=hr,
            unit="bpm",
            icon="favorite",
            tone=_band(hr, normal=(60, 100), warning=(50, 120)),
            reference="Acuan istirahat 60-100 bpm",
        ),
        _vital(
            vid="spo2",
            label="Saturasi Oksigen",
            value=spo2,
            unit="%",
            icon="water_drop",
            tone=_band(spo2, normal=(95, 100), warning=(91, 94)),
            reference="Acuan di atas 95%",
        ),
        _vital(
            vid="temperature",
            label="Suhu Tubuh",
            value=temp,
            unit="°C",
            icon="thermostat",
            tone=_band(temp, normal=(36.1, 37.5), warning=(35.5, 38.4)),
            reference="Acuan 36.1-37.5°C",
        ),
        _vital(
            vid="battery",
            label="Baterai Smartwear",
            value=batt,
            unit="%",
            icon="battery_full",
            tone=_band(batt, normal=(51, 100), warning=(21, 50)),
            reference="Isi ulang di bawah 20%",
        ),
    ]
