"""Starts the JagSi API with backend/.env.demo loaded first (terminal A).

    python -m demo.serve                  (run from backend/)

``app.config`` reads the environment once, when it is imported, so the demo
settings (topic prefix, device ID, database path) must be in the environment
before uvicorn imports the app. This replaces the one-line wrapper in section
11 of docs/wokwi-team-requirements.md and works the same in PowerShell, macOS
and Linux.
"""

from __future__ import annotations

import os

from demo.cloud import ENV_FILE, load_env_file


def main() -> None:
    if not ENV_FILE.exists():
        print(f"note: {ENV_FILE} not found, starting without cloud settings")
    load_env_file()
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.getenv("JAGSI_API_HOST", "127.0.0.1"),
        port=int(os.getenv("JAGSI_API_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
