"""Shared hosted demo pairing: one code, many signed-in accounts.

The code is provisioned for a deployment, not per device: any Google account may
redeem it against the one configured simulated watch. This locks in the demo
contract (multi-presenter, multi-audience) so a future "single owner" change
fails loudly here instead of breaking the rehearsal silently.
"""

from __future__ import annotations

import asyncio
import hashlib
import sqlite3

import pytest
from fastapi import HTTPException

from app.hosted_pairing import redeem


CODE = "demo-code-for-shared-pairing"
DIGEST = hashlib.sha256(CODE.encode()).hexdigest()


class _Response:
    status_code = 200

    def __init__(self, user_id: str):
        self._user_id = user_id

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return {"id": self._user_id}


class _Client:
    def __init__(self, user_id: str):
        self._user_id = user_id

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers=None):
        assert headers and headers["Authorization"].startswith("Bearer ")
        return _Response(self._user_id)


def _env(monkeypatch, tmp_path, user_id: str):
    monkeypatch.setenv("JAGSI_HOSTED_PAIRING_SHA256", DIGEST)
    monkeypatch.setenv("JAGSI_SUPABASE_URL", "https://supabase.example")
    monkeypatch.setenv("JAGSI_SUPABASE_PUBLISHABLE_KEY", "pub-key")
    monkeypatch.setenv("JAGSI_LOCAL_VITALS", "1")
    monkeypatch.setattr("app.hosted_pairing.httpx.AsyncClient", lambda timeout=5: _Client(user_id))
    return str(tmp_path / "pairing.db")


def test_same_code_redeemable_by_many_accounts(monkeypatch, tmp_path):
    database = _env(monkeypatch, tmp_path, "presenter")
    asyncio.run(redeem(CODE, "Bearer presenter-token", database))
    # A second, distinct Google account redeems the same code: no conflict.
    monkeypatch.setattr("app.hosted_pairing.httpx.AsyncClient", lambda timeout=5: _Client("audience"))
    asyncio.run(redeem(CODE, "Bearer audience-token", database))

    with sqlite3.connect(database) as connection:
        rows = connection.execute(
            "SELECT digest, user_id FROM hosted_demo_pairing ORDER BY user_id"
        ).fetchall()
    assert rows == [(DIGEST, "audience"), (DIGEST, "presenter")]


def test_same_account_redeem_is_idempotent(monkeypatch, tmp_path):
    database = _env(monkeypatch, tmp_path, "presenter")
    asyncio.run(redeem(CODE, "Bearer presenter-token", database))
    asyncio.run(redeem(CODE, "Bearer presenter-token", database))

    with sqlite3.connect(database) as connection:
        count = connection.execute("SELECT COUNT(*) FROM hosted_demo_pairing").fetchone()[0]
    assert count == 1


def test_wrong_code_rejected_even_when_signed_in(monkeypatch, tmp_path):
    database = _env(monkeypatch, tmp_path, "presenter")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(redeem("wrong-code-for-shared-pairing", "Bearer presenter-token", database))
    assert exc.value.status_code == 409


def test_missing_bearer_token_rejected(monkeypatch, tmp_path):
    database = _env(monkeypatch, tmp_path, "presenter")
    with pytest.raises(HTTPException) as exc:
        asyncio.run(redeem(CODE, "", database))
    assert exc.value.status_code == 401
