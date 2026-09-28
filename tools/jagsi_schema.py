"""JagSi MQTT contract v1: topic names and simple payload checks.

Shared by mqtt_monitor.py, fake_device.py and the tests.
Full description: docs/mqtt-contract.md
"""

TOPIC_BASE = "jagsi/abal/v1"
ALERT_TYPES = ("manual_sos", "fall_detected")


def topic(device_id: str, kind: str) -> str:
    """kind = telemetry | event | status | cmd"""
    return f"{TOPIC_BASE}/{device_id}/{kind}"


def split_topic(t: str):
    """'jagsi/abal/v1/<device>/<kind>' -> (device, kind), or (None, None) if not ours."""
    prefix = TOPIC_BASE + "/"
    if not t.startswith(prefix):
        return None, None
    rest = t[len(prefix):].split("/")
    if len(rest) != 2:
        return None, None
    return rest[0], rest[1]


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _check(problems, cond, msg):
    if not cond:
        problems.append(msg)


def _check_required(d, fields, problems):
    for f in fields:
        _check(problems, f in d, f"missing field '{f}'")


def _check_nullable_range(d, key, lo, hi, problems):
    if key not in d or d[key] is None:
        return
    x = d[key]
    _check(problems, _is_num(x), f"'{key}' must be a number or null")
    if _is_num(x):
        _check(problems, lo <= x <= hi, f"'{key}'={x} outside {lo}..{hi}")


def _check_vector(d, key, problems):
    vec = d.get(key)
    if not isinstance(vec, dict):
        problems.append(f"'{key}' must be an object with x, y, z")
        return
    for axis in ("x", "y", "z"):
        _check(problems, _is_num(vec.get(axis)), f"'{key}.{axis}' must be a number")


def _check_ts(d, problems):
    ts = d.get("ts")
    _check(problems, ts is None or (isinstance(ts, str) and ts.endswith("Z")),
           "'ts' must be null or an ISO 8601 UTC string ending with 'Z'")


def validate_telemetry(d: dict) -> list:
    p = []
    _check_required(d, ("device_id", "seq", "ts", "uptime_ms", "heart_rate", "spo2",
                        "body_temperature", "accel", "gyro", "accel_peak_g", "battery_level"), p)
    if p:
        return p
    _check(p, isinstance(d["device_id"], str) and d["device_id"], "'device_id' must be a non-empty string")
    _check(p, isinstance(d["seq"], int) and d["seq"] >= 1, "'seq' must be an int >= 1")
    _check_ts(d, p)
    _check(p, d["heart_rate"] is None or isinstance(d["heart_rate"], int), "'heart_rate' must be an int or null")
    _check_nullable_range(d, "heart_rate", 20, 250, p)
    _check_nullable_range(d, "spo2", 50, 100, p)
    _check_nullable_range(d, "body_temperature", 25, 45, p)
    _check_vector(d, "accel", p)
    _check_vector(d, "gyro", p)
    _check(p, _is_num(d["accel_peak_g"]) and d["accel_peak_g"] >= 0, "'accel_peak_g' must be a number >= 0")
    _check(p, isinstance(d["battery_level"], int) and 0 <= d["battery_level"] <= 100,
           "'battery_level' must be an int 0..100")
    return p


def validate_event(d: dict) -> list:
    p = []
    _check_required(d, ("device_id", "event_id", "ts", "uptime_ms", "alert_type",
                        "status", "attempt", "accel_peak_g", "vitals"), p)
    if p:
        return p
    _check(p, isinstance(d["event_id"], str) and d["event_id"], "'event_id' must be a non-empty string")
    _check_ts(d, p)
    _check(p, d["alert_type"] in ALERT_TYPES, f"'alert_type' must be one of {ALERT_TYPES}")
    _check(p, d["status"] == "unresolved", "'status' from the device must be 'unresolved'")
    _check(p, isinstance(d["attempt"], int) and d["attempt"] >= 1, "'attempt' must be an int >= 1")
    _check(p, isinstance(d["vitals"], dict), "'vitals' must be an object")
    return p


def validate_status(d: dict) -> list:
    p = []
    _check_required(d, ("device_id", "state"), p)
    if not p:
        _check(p, d["state"] in ("online", "offline"), "'state' must be 'online' or 'offline'")
    return p


VALIDATORS = {"telemetry": validate_telemetry, "event": validate_event, "status": validate_status}
