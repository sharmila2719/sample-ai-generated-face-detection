"""Lambda@Edge viewer-request handler — HMAC session-cookie auth for the web UI."""

from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Dict

# Paths that bypass auth
PUBLIC_PATHS = {"/api/session-check", "/api/health", "/health"}

# Session cookie name
_COOKIE_NAME = "session"

# HMAC secret (must match session_check_handler.py)
_SECRET = os.getenv("SESSION_HMAC_SECRET", "changeme-in-production")

# Session max age (seconds) — 24 hours
_SESSION_MAX_AGE = 86400


def lambda_handler(event: Dict[str, Any], _context: Any) -> Dict[str, Any]:
    request = event["Records"][0]["cf"]["request"]
    uri = request.get("uri", "/")

    # Allow public paths through
    if uri in PUBLIC_PATHS or uri.startswith("/api/session-check"):
        return request

    # Parse cookies
    cookies = _parse_cookies(request.get("headers", {}).get("cookie", []))
    session_token = cookies.get(_COOKIE_NAME)

    if session_token and _verify_session(session_token):
        return request  # authenticated

    # Redirect unauthenticated requests to the login page
    return {
        "status": "302",
        "statusDescription": "Found",
        "headers": {
            "location": [{"key": "Location", "value": "/login.html"}],
            "cache-control": [{"key": "Cache-Control", "value": "no-store"}],
        },
    }


def _parse_cookies(cookie_headers: list) -> Dict[str, str]:
    cookies: Dict[str, str] = {}
    for header in cookie_headers:
        for pair in header.get("value", "").split(";"):
            pair = pair.strip()
            if "=" in pair:
                name, _, value = pair.partition("=")
                cookies[name.strip()] = value.strip()
    return cookies


def _verify_session(token: str) -> bool:
    """Verify the HMAC-signed session token."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return False
        username, ts_str, sig = parts
        ts = int(ts_str)
        if time.time() - ts > _SESSION_MAX_AGE:
            return False
        payload = f"{username}:{ts_str}"
        expected_sig = hmac.new(_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(sig, expected_sig)
    except Exception:
        return False
