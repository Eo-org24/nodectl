from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def sign_payload(payload: dict, secret_key: str) -> str:
    body = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = hmac.new(secret_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64encode(signature)}"


def unsign_payload(token: str, secret_key: str) -> dict | None:
    try:
        body, signature = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(secret_key.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    if not hmac.compare_digest(expected, _b64decode(signature)):
        return None
    try:
        return json.loads(_b64decode(body).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def new_csrf_token() -> str:
    return secrets.token_urlsafe(24)


@dataclass(frozen=True)
class SessionUser:
    username: str
    role: str
    csrf_token: str
    terminal_target: str
