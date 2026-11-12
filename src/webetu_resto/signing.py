"""HMAC request signing for the ONOU resto API.

The Android app signs every resto request with:

    message = f"{timestamp}|{nonce}|{raw_body}"

where ``raw_body`` is the exact JSON string that is sent (empty for GET, and a
compact JSON body for POST/DELETE calls). The signature is the lowercase hex
HMAC-SHA256 of that message with the app-wide key.

This module is deliberately pure so it can be tested against golden vectors.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid

DEFAULT_HMAC_SECRET = "pUzHUW2WX54uCzhO8JC2eQ6g1Ol21upw"


def sign(secret: str | bytes, timestamp: str, nonce: str, raw_body: str) -> str:
    """Return the hex HMAC-SHA256 signature for one request."""
    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    message = f"{timestamp}|{nonce}|{raw_body}".encode()
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def make_signature_headers(
    secret: str | bytes,
    raw_body: str,
    *,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    """Build the three signed headers for one request.

    ``timestamp`` and ``nonce`` are injectable for deterministic tests.
    """
    ts = str(int(time.time()) if timestamp is None else timestamp)
    value = nonce or str(uuid.uuid4())
    return {
        "X-Timestamp": ts,
        "X-Nonce": value,
        "X-Signature": sign(secret, ts, value, raw_body),
    }
