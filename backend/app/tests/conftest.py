"""Test configuration.

``app.config`` reads the environment once at import time, so the database path is
redirected here, before any test module imports the application.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.mkdtemp(prefix="jagsi-test-"))
os.environ.setdefault("JAGSI_DB_PATH", str(_TMP / "test.db"))
os.environ.setdefault("JAGSI_MQTT_HOST", "127.0.0.1")
