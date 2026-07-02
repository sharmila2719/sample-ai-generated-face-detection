"""Lambda handler for POST /api/session-check — server-side web UI authentication."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

import boto3

from src.logger import get_logger

logger = get_logger(__name__)

_CORS = {
    "Access-Control-Allow-Origin": os.getenv("WEB_UI_ALLOWED_ORIGIN", "*"),
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST,OPTIONS",
    "Access-Control-Allow-Credentials": "true",
}

# In-memory cache for the secret (TTL = 300 s)
_secret_cache: Optional[Dict[str, str]] = None
_secret_cache_ts: float = 0.0
_SECRET_TTL = 300


def _get_users() -> Dict[str, str]:
    """Fetch the users map from Secrets Manager (cached for 300 s)."""
    global _secret_cache, _secret_cache_ts
    now = time.monotonic()
    if _secret_cache is not None and (now - _secret_cache_ts) < _SECRET_TTL:
        return _secret_cache

    secret_id = os.getenv("WEB_UI_PASSWORD_SECRET_ARN", "")
    if not secret_id:
        raise RuntimeError("WEB_UI_PASSWORD_SECRET_ARN not set")

    client = boto3.client("secretsmanager")
    resp = client.get_secret_value(SecretId=secret_id)
    payload = json.loads(resp["SecretString"])
    users: Dict[str, str] = payload.get("users", {})
    _secret_cache = users
    _secret_cache_ts = now
    return users


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    if (event.get("httpMethod") or "") == "OPTIONS":
        return {"statusCode": 204, "headers": _CORS, "body": ""}

    try:
        body = json.loads(event.get("body") or "{}")
        username = body.get("username", "")
        password = body.get("password", "")
    except json.JSONDecodeError:
        return _respond(400, {"outcome": "invalid_request"})

    try:
        users = _get_users()
    except Exception as exc:
        logger.error("session_check.secret_unavailable", extra={"error": str(exc), "outcome": "secret_unavailable"})
        return _respond(503, {"outcome": "secret_unavailable"})

    expected_password = users.get(username)
    if expected_password and hmac.compare_digest(password, expected_password):
        # Issue a signed session cookie
        session_token = _make_session_token(username)
        headers = {
            **_CORS,
            "Set-Cookie": (
                f"session={session_token}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=86400"
            ),
        }
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"outcome": "authenticated", "username": username}),
        }

    return _respond(401, {"outcome": "invalid_credentials"})


def _make_session_token(username: str) -> str:
    secret = os.getenv("SESSION_HMAC_SECRET", "changeme-in-production")
    ts = str(int(time.time()))
    payload = f"{username}:{ts}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def _respond(status: int, body: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", **_CORS},
        "body": json.dumps(body),
    }
