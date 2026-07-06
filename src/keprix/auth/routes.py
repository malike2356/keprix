"""Authentication HTTP routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.auth.config import auth_enabled, multi_user_enabled
from keprix.auth.dependencies import get_current_user
from keprix.auth.session import auth_manager
from keprix.security.audit import audit_log
from keprix.security.rate_limiter import rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str | None = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class TotpVerifyRequest(BaseModel):
    code: str


@router.post("/login")
async def login(body: LoginRequest, request: Request) -> dict[str, Any]:
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limit("auth_login", client_ip, limit=5, window_seconds=600):
        raise HTTPException(status_code=429, detail="Too many login attempts", headers={"Retry-After": "600"})

    token, user, error = auth_manager.login(body.username, body.password, totp_code=body.totp_code)
    if not token or not user:
        await audit_log(
            "login_failed",
            user_id=body.username,
            ip_address=client_ip,
            severity="warn",
            event_data={"reason": error},
        )
        raise HTTPException(status_code=401, detail=error or "Invalid credentials")

    await audit_log("login", user_id=user["id"], ip_address=client_ip)
    return {"token": token, "user": _public_user(user)}


@router.post("/logout")
async def logout(request: Request, user: dict = Depends(get_current_user)) -> dict[str, bool]:
    token = getattr(request.state, "auth_token", None)
    if token:
        auth_manager.revoke_token(token)
    await audit_log("logout", user_id=user.get("id"), ip_address=request.client.host if request.client else None)
    return {"ok": True}


@router.post("/register")
async def register(body: RegisterRequest, request: Request) -> dict[str, Any]:
    if not multi_user_enabled():
        raise HTTPException(status_code=403, detail="Registration disabled")
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limit("auth_register", client_ip, limit=3, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Too many registration attempts", headers={"Retry-After": "3600"})
    ok, message = auth_manager.register(body.username, body.password, email=body.email)
    if not ok:
        raise HTTPException(status_code=400, detail=message)
    return {"ok": True, "message": message}


@router.get("/config")
async def auth_config() -> dict[str, Any]:
    return {
        "auth_enabled": auth_enabled(),
        "multi_user": multi_user_enabled(),
    }


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": _public_user(user)}


@router.post("/totp/setup")
async def totp_setup(user: dict = Depends(get_current_user)) -> dict[str, str]:
    secret, uri = auth_manager.totp_setup(user["username"])
    return {"secret": secret, "provisioning_uri": uri}


@router.post("/totp/verify")
async def totp_verify(body: TotpVerifyRequest, user: dict = Depends(get_current_user)) -> dict[str, bool]:
    if not auth_manager.totp_confirm(user["username"], body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    return {"ok": True}


@router.post("/totp/disable")
async def totp_disable(body: TotpVerifyRequest, user: dict = Depends(get_current_user)) -> dict[str, bool]:
    if not auth_manager.totp_disable(user["username"], body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    return {"ok": True}


def _public_user(user: dict | None) -> dict[str, Any]:
    if not user:
        return {}
    return {
        "id": user.get("id"),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role", "user"),
        "totp_enabled": user.get("totp_enabled", False),
        "is_approved": user.get("is_approved", True),
    }
