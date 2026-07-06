"""HMAC-signed review tokens."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _secret_path() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home()) / "review_gateway"
    except Exception:
        root = Path.home() / ".keprix" / "review_gateway"
    root.mkdir(parents=True, exist_ok=True)
    return root / "hmac_secret"


def get_review_secret() -> bytes:
    env = os.environ.get("REVIEW_GATEWAY_HMAC_SECRET", "").strip()
    if env:
        return env.encode("utf-8")
    path = _secret_path()
    if path.exists():
        return path.read_bytes()
    secret = secrets.token_bytes(32)
    path.write_bytes(secret)
    return secret


def generate_review_token(
    review_request_id: str,
    workspace_id: str,
    expires_at: datetime,
    secret_key: bytes | None = None,
) -> tuple[str, str]:
    secret = secret_key or get_review_secret()
    token_id = str(uuid.uuid4())
    msg = f"{token_id}:{review_request_id}:{workspace_id}:{expires_at.isoformat()}"
    token_hash = hmac.new(secret, msg.encode(), hashlib.sha256).hexdigest()
    raw = f"{token_id}:{token_hash}"
    url_token = base64.urlsafe_b64encode(raw.encode()).decode().rstrip("=")
    return token_id, url_token


def decode_url_token(url_token: str) -> tuple[str, str] | None:
    try:
        padded = url_token + "=" * ((4 - len(url_token) % 4) % 4)
        raw = base64.urlsafe_b64decode(padded).decode()
        token_id, provided_hash = raw.split(":", 1)
        return token_id, provided_hash
    except Exception:
        return None


def validate_review_token(
    url_token: str,
    *,
    token_id: str,
    review_request_id: str,
    workspace_id: str,
    expires_at: datetime,
    status: str,
    secret_key: bytes | None = None,
) -> bool:
    if status != "pending":
        return False
    now = datetime.now(timezone.utc)
    exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    if now > exp:
        return False
    decoded = decode_url_token(url_token)
    if decoded is None:
        return False
    decoded_id, provided_hash = decoded
    if decoded_id != token_id:
        return False
    secret = secret_key or get_review_secret()
    msg = f"{token_id}:{review_request_id}:{workspace_id}:{expires_at.isoformat()}"
    expected = hmac.new(secret, msg.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, provided_hash)
