"""Carina Visual Playbook Studio handoff JWT verification."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

STUDIO_HANDOFF_AUDIENCE = "keprix-studio"
HANDOFF_TTL_SECONDS = 5 * 60


class StudioHandoffError(Exception):
    pass


@dataclass(frozen=True)
class StudioHandoffClaims:
    sub: str
    tenant_id: str
    carina_user_id: str
    aud: str
    exp: int
    iat: int


def handoff_secret() -> str | None:
    value = os.environ.get("KEPRIX_HANDOFF_SECRET", "").strip()
    return value or None


def _decode_segment(segment: str) -> dict[str, Any]:
    padding = "=" * (-len(segment) % 4)
    raw = base64.urlsafe_b64decode(segment + padding)
    return json.loads(raw.decode("utf-8"))


def verify_studio_handoff_token(token: str, *, now: int | None = None) -> StudioHandoffClaims:
    secret = handoff_secret()
    if not secret or len(secret) < 16:
        raise StudioHandoffError("Studio handoff is not configured")

    parts = token.split(".")
    if len(parts) != 3:
        raise StudioHandoffError("Invalid handoff token")

    header_b64, body_b64, signature_b64 = parts
    expected = hmac.new(
        secret.encode("utf-8"),
        f"{header_b64}.{body_b64}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    try:
        provided = base64.urlsafe_b64decode(signature_b64 + "=" * (-len(signature_b64) % 4))
    except Exception as exc:
        raise StudioHandoffError("Invalid handoff token signature") from exc
    if not hmac.compare_digest(provided, expected):
        raise StudioHandoffError("Invalid handoff token signature")

    payload = _decode_segment(body_b64)
    current = now if now is not None else int(time.time())
    if payload.get("aud") != STUDIO_HANDOFF_AUDIENCE:
        raise StudioHandoffError("Invalid handoff audience")
    exp = payload.get("exp")
    if not isinstance(exp, int) or exp <= current:
        raise StudioHandoffError("Handoff token expired")

    sub = str(payload.get("sub") or "").strip()
    tenant_id = str(payload.get("tenant_id") or "").strip()
    carina_user_id = str(payload.get("carina_user_id") or "").strip()
    iat = payload.get("iat")
    if not sub or not tenant_id or not carina_user_id or not isinstance(iat, int):
        raise StudioHandoffError("Invalid handoff claims")

    return StudioHandoffClaims(
        sub=sub,
        tenant_id=tenant_id,
        carina_user_id=carina_user_id,
        aud=str(payload.get("aud")),
        exp=exp,
        iat=iat,
    )


def handoff_username(claims: StudioHandoffClaims) -> str:
    raw = f"carina-{claims.tenant_id}-{claims.carina_user_id}".lower()
    cleaned = re.sub(r"[^a-z0-9._-]+", "-", raw).strip("-")
    return (cleaned or "carina-user")[:48]
