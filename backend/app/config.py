"""Runtime settings, all overridable by environment variable.

Defaults match the Sprint 1 development setup in docs/mqtt-contract.md so that
``uvicorn app.main:app`` works with no configuration at all.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    # MQTT broker. The public broker is development only; Azure IoT Hub with
    # device certificates replaces it in issue #8.
    mqtt_host: str = os.getenv("JAGSI_MQTT_HOST", "broker.hivemq.com")
    mqtt_port: int = int(os.getenv("JAGSI_MQTT_PORT", "1883"))
    mqtt_username: str | None = os.getenv("JAGSI_MQTT_USERNAME") or None
    mqtt_password: str | None = os.getenv("JAGSI_MQTT_PASSWORD") or None

    topic_base: str = os.getenv("JAGSI_TOPIC_BASE", "jagsi/abal/v1/")
    device_id: str = os.getenv("JAGSI_DEVICE_ID", "jagsi-watch-01")

    db_path: str = os.getenv("JAGSI_DB_PATH", str(BACKEND_DIR / "data" / "jagsi.db"))

    model_path: str = os.getenv(
        "JAGSI_MODEL_PATH", str(BACKEND_DIR / "ml" / "artifacts" / "fall_clf.joblib")
    )
    # Scoring motion windows can be turned off to run the API without the model.
    enable_classifier: bool = _env_bool("JAGSI_ENABLE_CLASSIFIER", True)
    # Overrides the decision threshold stored in the artifact, without retraining.
    # The stored value is 0.11, which scripts/validate_on_device_windows.py shows
    # flags ordinary walking as a fall. Set JAGSI_FALL_THRESHOLD while the model
    # is being re-tuned; leave unset to use whatever the artifact carries.
    fall_threshold: float | None = (
        float(os.environ["JAGSI_FALL_THRESHOLD"])
        if os.getenv("JAGSI_FALL_THRESHOLD")
        else None
    )
    # The device rule fires within 100 ms; an ML alert for the same fall arriving
    # inside this window is treated as the same event and dropped.
    duplicate_window_seconds: int = int(os.getenv("JAGSI_DUPLICATE_WINDOW_S", "10"))
    # Minimum gap between two ML alerts for one device, so a fall that stays in
    # three overlapping windows does not alert three times.
    ml_alert_cooldown_seconds: int = int(os.getenv("JAGSI_ML_COOLDOWN_S", "15"))

    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv(
                "JAGSI_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
            ).split(",")
            if o.strip()
        ]
    )

    def topic(self, suffix: str, device_id: str | None = None) -> str:
        return f"{self.topic_base}{device_id or self.device_id}/{suffix}"

    @property
    def subscribe_pattern(self) -> str:
        """Every topic from every device: jagsi/abal/v1/+/#

        Kept for documentation and the health endpoint. The bridge does NOT use
        it: that wildcard also matches ``cmd``, which the bridge publishes itself,
        so it would receive its own commands back from the broker.
        """
        return f"{self.topic_base}+/#"

    @property
    def subscribe_topics(self) -> list[tuple[str, int]]:
        """Only the device-to-cloud topics, so the bridge never echoes itself."""
        return [
            (f"{self.topic_base}+/telemetry", 0),
            (f"{self.topic_base}+/motion", 0),
            (f"{self.topic_base}+/event", 0),
            (f"{self.topic_base}+/status", 0),
        ]


settings = Settings()
