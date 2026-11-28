"""Opt-in local simulated sensor producer for dashboard and brief testing."""
import asyncio
import random
import time

from .store import utcnow
from .vitals import telemetry_to_vitals

PROFILES = {
    "stable": (76, 98, 36.7, "normal"),
    "attention": (109, 93, 38.0, "warning"),
    "critical": (132, 89, 38.7, "critical"),
}


def samples(profile, seed=None):
    hr, oxygen, temp, tone = PROFILES[profile]
    baseline = (hr, oxygen, temp)
    current = baseline
    rng = random.Random(seed)
    while True:
        candidate = tuple(round(center + .8 * (value - center) + rng.gauss(0, noise), digits)
                          for center, value, noise, digits in zip(
                              baseline, current, (1.5, .13, .04), (0, 2, 2)))
        reading = dict(zip(("heart_rate", "spo2", "body_temperature"), candidate))
        reading["heart_rate"] = int(reading["heart_rate"])
        if all(v["tone"] == tone for v in telemetry_to_vitals(reading)[:3]):
            current = candidate
            yield reading


async def stream(store, publish, device_id, controls, seed):
    start = time.monotonic()
    sequence = 0
    generators = {profile: samples(profile, seed) for profile in PROFILES}
    while True:
        profile = controls["profile"]
        if profile == "paused":
            await asyncio.sleep(2)
            continue
        reading = next(generators[profile])
        sequence += 1
        def persist():
            store.insert_telemetry(dict(
                reading, device_id=device_id, seq=sequence, ts=utcnow(),
                uptime_ms=int((time.monotonic() - start) * 1000), battery_level=87, sim=True,
            ))
            return store.latest_telemetry(device_id)

        publish({"type": "telemetry", "data": await asyncio.to_thread(persist)})
        await asyncio.sleep(2)
