"""Signed embed tokens and origin allowlist (Prompt 630)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any


def embed_signing_key() -> str:
    return (
        (os.environ.get("KEPRIX_CONCIERGE_EMBED_SECRET") or "").strip()
        or (os.environ.get("CHANNEL_SHIELD_WEB_EMBED_KEY") or "").strip()
        or "keprix-concierge-embed-dev"
    )


def new_embed_nonce() -> str:
    return secrets.token_hex(16)


def sign_widget_embed_config(payload: dict[str, Any]) -> str:
    body = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode(
        "ascii"
    ).rstrip("=")
    sig = hmac.new(embed_signing_key().encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("ascii").rstrip("=")
    return f"{body}.{sig_b64}"


def verify_widget_embed_config(
    token: str,
    *,
    expected_persona_id: str,
) -> dict[str, Any] | None:
    try:
        body, sig = token.split(".", 1)
    except ValueError:
        return None
    expected = hmac.new(
        embed_signing_key().encode("utf-8"), body.encode("ascii"), hashlib.sha256
    ).digest()
    expected_b64 = base64.urlsafe_b64encode(expected).decode("ascii").rstrip("=")
    if not hmac.compare_digest(sig, expected_b64):
        return None
    pad = "=" * (-len(body) % 4)
    try:
        parsed = json.loads(base64.urlsafe_b64decode(body + pad).decode("utf-8"))
    except Exception:
        return None
    if str(parsed.get("personaId") or "") != expected_persona_id:
        return None
    if not parsed.get("workspaceId") or not parsed.get("nonce"):
        return None
    exp = parsed.get("exp")
    if not isinstance(exp, (int, float)) or time.time() * 1000 > float(exp):
        return None
    return parsed


def is_origin_allowed(origin: str | None, allowlist: list[str] | None) -> bool:
    if not allowlist:
        return True
    if not origin:
        return False
    normalized = origin.strip().lower().rstrip("/")
    for entry in allowlist:
        allowed = entry.strip().lower().rstrip("/")
        if allowed and allowed == normalized:
            return True
    return False
