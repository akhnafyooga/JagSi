"""Redeem a deployment-provisioned code for the fictional-data rehearsal.

The hosted code is a single shared demo code: any signed-in Google account may
redeem it, so every presenter or audience account can walk the same setup flow
against the one configured simulated watch. It does NOT pair physical hardware
and does NOT create per-account telemetry authorization.
"""
import hashlib
import hmac
import os
import sqlite3

import httpx
from fastapi import HTTPException


async def require_supabase_user(authorization: str) -> str:
    url = os.getenv("JAGSI_SUPABASE_URL", "").rstrip("/")
    key = os.getenv("JAGSI_SUPABASE_PUBLISHABLE_KEY", "")
    if not url or not key:
        raise HTTPException(503, "Sign-in verification is unavailable.")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401)
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url + "/auth/v1/user", headers={
                "apikey": key, "Authorization": authorization,
            })
        if response.status_code in (401, 403):
            raise HTTPException(401)
        response.raise_for_status()
        user_id = response.json()["id"]
    except (httpx.HTTPError, ValueError, KeyError):
        raise HTTPException(503, "Layanan autentikasi tidak tersedia.") from None
    if not isinstance(user_id, str) or not user_id:
        raise HTTPException(503, "Sign-in verification is unavailable.")
    return user_id


async def redeem(code, authorization, database):
    digest = os.getenv("JAGSI_HOSTED_PAIRING_SHA256", "")
    if not all((digest, os.getenv("JAGSI_SUPABASE_URL"), os.getenv("JAGSI_SUPABASE_PUBLISHABLE_KEY"), os.getenv("JAGSI_LOCAL_VITALS"))):
        raise HTTPException(404)
    user_id = await require_supabase_user(authorization)
    supplied = hashlib.sha256(code.encode()).hexdigest()
    if not hmac.compare_digest(supplied, digest):
        raise HTTPException(409, "Kode tidak berlaku.")
    with sqlite3.connect(database) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS hosted_demo_pairing (
            digest TEXT, user_id TEXT NOT NULL, redeemed_at TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (digest, user_id))""")
        info = connection.execute("PRAGMA table_info(hosted_demo_pairing)").fetchall()
        cols = [row[1] for row in info]
        if cols == ["digest", "user_id"]:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS hosted_demo_pairing_new (
                digest TEXT, user_id TEXT NOT NULL, redeemed_at TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (digest, user_id))""")
            connection.execute(
                "INSERT OR IGNORE INTO hosted_demo_pairing_new (digest, user_id) "
                "SELECT digest, user_id FROM hosted_demo_pairing")
            connection.execute("DROP TABLE hosted_demo_pairing")
            connection.execute("ALTER TABLE hosted_demo_pairing_new RENAME TO hosted_demo_pairing")
        try:
            from datetime import datetime, timezone
            now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            now = ""
        connection.execute(
            "INSERT OR IGNORE INTO hosted_demo_pairing (digest, user_id, redeemed_at) "
            "VALUES (?, ?, ?)", (digest, user_id, now))
