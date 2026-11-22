"""R12: the database URI stays in backend environment variables.

Cheap static checks that run without PostgreSQL. They protect against the two
realistic leaks: committing backend/.env.demo, and exposing the URI to the
browser through a NEXT_PUBLIC_ variable.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
FRONTEND = REPO / "frontend"


def test_env_file_is_gitignored():
    rules = (REPO / ".gitignore").read_text().splitlines()
    assert "backend/.env.demo" in rules


def test_example_holds_placeholders_only():
    text = (REPO / "backend" / ".env.demo.example").read_text()
    dsn = re.search(r"^JAGSI_CLOUD_DSN=(.*)$", text, re.M).group(1)
    assert "URL_ENCODED_PASSWORD" in dsn
    assert re.search(r"^JAGSI_SOURCE_ID=PASTE_", text, re.M)


def test_frontend_never_references_cloud_credentials():
    offenders = []
    for path in FRONTEND.rglob("*"):
        if any(part in {"node_modules", ".next"} for part in path.parts):
            continue
        if path.suffix not in {".ts", ".tsx", ".js", ".mjs", ".json", ".local", ".example"}:
            continue
        text = path.read_text(errors="ignore")
        if "CLOUD_DSN" in text or "supabase.co" in text or "pooler.supabase.com" in text:
            offenders.append(str(path.relative_to(REPO)))
    assert offenders == []


def test_cloud_module_never_logs_the_dsn():
    source = (REPO / "backend" / "demo" / "cloud.py").read_text()
    assert not re.search(r"log\.\w+\([^)]*\.dsn", source)
