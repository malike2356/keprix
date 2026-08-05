"""Consume Carina studio handoff tokens and mint Keprix sessions."""

from __future__ import annotations

import secrets
import time
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.auth.request_context import client_ip, client_label
from keprix.auth.session import auth_manager
from keprix.auth.studio_handoff import (
    StudioHandoffError,
    handoff_username,
    verify_studio_handoff_token,
)
from keprix.security.audit import audit_log
from keprix.security.rate_limiter import rate_limit

router = APIRouter(prefix="/api/auth/handoff", tags=["auth-handoff"])

_CONSUMED: dict[str, float] = {}


def _consumed_path() -> Path:
    try:
        from keprix_cli.config import get_keprix_home

        root = Path(get_keprix_home())
    except Exception:
        root = Path.home() / ".keprix"
    return root / "studio_handoff_consumed.json"


def _load_consumed() -> dict[str, float]:
    path = _consumed_path()
    if not path.exists():
        return {}
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return {str(key): float(value) for key, value in payload.items()}
    except Exception:
        return {}
    return {}


def _save_consumed(items: dict[str, float]) -> None:
    import json

    path = _consumed_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items), encoding="utf-8")


def _prune_consumed(items: dict[str, float], *, now: float) -> dict[str, float]:
    return {key: expiry for key, expiry in items.items() if expiry > now}


def _mark_consumed(token: str, *, expires_at: int) -> None:
    global _CONSUMED
    now = time.time()
    _CONSUMED = _prune_consumed(_CONSUMED or _load_consumed(), now=now)
    _CONSUMED[token] = float(expires_at)
    _save_consumed(_CONSUMED)


def _already_consumed(token: str) -> bool:
    global _CONSUMED
    now = time.time()
    _CONSUMED = _prune_consumed(_CONSUMED or _load_consumed(), now=now)
    return token in _CONSUMED


class HandoffConsumeBody(BaseModel):
    token: str = Field(..., min_length=20, max_length=4096)


def _ensure_handoff_user(claims) -> dict[str, Any]:
    username = handoff_username(claims)
    user = auth_manager.get_user(username)
    if user is None:
        password = secrets.token_urlsafe(32)
        email = claims.sub if "@" in claims.sub else None
        user = auth_manager.create_user(
            username,
            password,
            role="user",
            email=email,
            is_approved=True,
        )
    user_id = str(user["id"])
    updated = auth_manager.update_user(
        user_id,
        email=claims.sub if "@" in claims.sub and not user.get("email") else user.get("email"),
    )
    user = auth_manager.attach_handoff_metadata(
        user_id,
        workspace_id=claims.tenant_id,
        carina_user_id=claims.carina_user_id,
        display_name=claims.sub,
    ) or updated or user
    return user


def _public_handoff_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "display_name": user.get("display_name") or user.get("username"),
        "email": user.get("email"),
        "avatar_url": user.get("avatar_url"),
        "locale": user.get("locale"),
        "timezone": user.get("timezone"),
        "role": user.get("role", "user"),
        "workspace_id": user.get("workspace_id"),
        "auth_source": user.get("auth_source"),
    }


@router.post("/consume")
async def consume_handoff(body: HandoffConsumeBody, request: Request) -> dict[str, Any]:
    ip = client_ip(request)
    if not rate_limit("auth_handoff_consume", ip, limit=20, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many handoff attempts", headers={"Retry-After": "60"})

    try:
        claims = verify_studio_handoff_token(body.token.strip())
    except StudioHandoffError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    if _already_consumed(body.token.strip()):
        raise HTTPException(status_code=401, detail="Handoff token already used")

    user = _ensure_handoff_user(claims)
    token = auth_manager.create_session(
        str(user["username"]),
        device_label=client_label(request) or "Carina studio handoff",
        ip_address=ip,
    )
    _mark_consumed(body.token.strip(), expires_at=claims.exp)

    await audit_log(
        "studio_handoff",
        user_id=str(user.get("id")),
        ip_address=ip,
        event_data={
            "tenant_id": claims.tenant_id,
            "carina_user_id": claims.carina_user_id,
        },
    )
    return {"token": token, "user": _public_handoff_user(user)}
