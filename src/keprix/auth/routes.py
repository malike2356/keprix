"""Authentication HTTP routes."""

from __future__ import annotations

import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from keprix.auth.config import auth_enabled, multi_user_enabled, otp_login_enabled, otp_step_up_enabled
from keprix.auth.dependencies import get_current_user
from keprix.auth.request_context import client_ip, client_label
from keprix.auth.session import auth_manager
from keprix.security.audit import audit_log
from keprix.security.rate_limiter import rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    totp_code: str | None = None
    recovery_code: str | None = None


class RegisterRequest(BaseModel):
    username: str
    password: str
    email: str | None = None


class TotpVerifyRequest(BaseModel):
    code: str


class TotpDisableRequest(BaseModel):
    password: str
    code: str | None = None
    recovery_code: str | None = None
    step_up_token: str | None = None


class TotpQrRequest(BaseModel):
    provisioning_uri: str = Field(..., min_length=12, max_length=2048)


class RecoveryGenerateRequest(BaseModel):
    password: str


class ProfileUpdateRequest(BaseModel):
    display_name: str | None = Field(None, max_length=120)
    email: str | None = Field(None, max_length=320)
    avatar_url: str | None = Field(None, max_length=2048)
    locale: str | None = Field(None, max_length=16)
    timezone: str | None = Field(None, max_length=64)


@router.post("/login")
async def login(body: LoginRequest, request: Request) -> dict[str, Any]:
    ip = client_ip(request)
    if not rate_limit("auth_login", ip, limit=5, window_seconds=600):
        raise HTTPException(status_code=429, detail="Too many login attempts", headers={"Retry-After": "600"})

    token, user, error = auth_manager.login(
        body.username,
        body.password,
        totp_code=body.totp_code,
        recovery_code=body.recovery_code,
        device_label=client_label(request),
        ip_address=ip,
    )
    if not token or not user:
        await audit_log(
            "login_failed",
            user_id=body.username,
            ip_address=ip,
            severity="warn",
            event_data={"reason": error},
        )
        if error == "totp_required":
            raise HTTPException(
                status_code=403,
                detail={"code": "totp_required", "message": "Two-factor authentication required"},
            )
        raise HTTPException(status_code=401, detail=error or "Invalid credentials")

    if body.recovery_code:
        await audit_log(
            "recovery_code_used",
            user_id=user["id"],
            ip_address=ip,
            event_data={"context": "login"},
        )

    await audit_log("login", user_id=user["id"], ip_address=ip)
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
        "otp_login_enabled": otp_login_enabled(),
        "otp_step_up_enabled": otp_step_up_enabled(),
    }


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": _public_user(user)}


@router.patch("/me")
async def update_me(
    body: ProfileUpdateRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    payload = body.model_dump(exclude_unset=True)
    if not payload:
        return {"user": _public_user(user)}

    if "email" in payload and payload["email"] is not None:
        payload["email"] = str(payload["email"]).strip().lower()

    try:
        updated = auth_manager.update_profile(str(user["id"]), **payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if updated is None:
        raise HTTPException(status_code=404, detail="User not found")

    changed_fields = sorted(payload.keys())
    await audit_log(
        "profile_updated",
        user_id=user.get("id"),
        ip_address=request.client.host if request.client else None,
        event_data={"fields": changed_fields},
    )
    return {"user": _public_user(updated)}


@router.post("/totp/setup")
async def totp_setup(user: dict = Depends(get_current_user)) -> dict[str, str]:
    secret, uri = auth_manager.totp_setup(user["username"])
    return {"secret": secret, "provisioning_uri": uri}


@router.post("/totp/verify")
async def totp_verify(body: TotpVerifyRequest, user: dict = Depends(get_current_user)) -> dict[str, Any]:
    was_enabled = bool(user.get("totp_enabled"))
    if not auth_manager.totp_confirm(user["username"], body.code):
        raise HTTPException(status_code=400, detail="Invalid TOTP code")
    recovery_codes: list[str] = []
    if not was_enabled:
        recovery_codes = auth_manager.generate_recovery_codes(user["username"])
    return {"ok": True, "recovery_codes": recovery_codes}


@router.post("/totp/qr")
async def totp_qr(body: TotpQrRequest, user: dict = Depends(get_current_user)) -> Response:
    del user
    uri = body.provisioning_uri.strip()
    if not uri.startswith("otpauth://"):
        raise HTTPException(status_code=400, detail="Invalid provisioning URI")
    try:
        import qrcode
    except ImportError as exc:
        raise HTTPException(status_code=503, detail="QR generation is unavailable on this server") from exc
    image = qrcode.make(uri)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return Response(content=buffer.getvalue(), media_type="image/png")


@router.post("/totp/recovery/generate")
async def totp_recovery_generate(
    body: RecoveryGenerateRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    if not auth_manager.verify_user_password(str(user["id"]), body.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    if not user.get("totp_enabled"):
        raise HTTPException(status_code=400, detail="Two-factor is not enabled")
    try:
        recovery_codes = auth_manager.generate_recovery_codes(user["username"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await audit_log(
        "recovery_codes_regenerated",
        user_id=user.get("id"),
        ip_address=request.client.host if request.client else None,
    )
    return {"recovery_codes": recovery_codes}


@router.post("/totp/disable")
async def totp_disable(body: TotpDisableRequest, user: dict = Depends(get_current_user)) -> dict[str, bool]:
    if not body.code and not body.recovery_code and not body.step_up_token:
        raise HTTPException(status_code=400, detail="TOTP code, recovery code, or email step-up required")
    if not auth_manager.totp_disable(
        user["username"],
        password=body.password,
        code=body.code,
        recovery_code=body.recovery_code,
        step_up_token=body.step_up_token,
    ):
        raise HTTPException(status_code=400, detail="Invalid credentials or verification code")
    return {"ok": True}


def _public_user(user: dict | None) -> dict[str, Any]:
    if not user:
        return {}
    username = user.get("username")
    display_name = user.get("display_name") or username
    return {
        "id": user.get("id"),
        "username": username,
        "display_name": display_name,
        "email": user.get("email"),
        "avatar_url": user.get("avatar_url"),
        "locale": user.get("locale"),
        "timezone": user.get("timezone"),
        "role": user.get("role", "user"),
        "totp_enabled": user.get("totp_enabled", False),
        "is_approved": user.get("is_approved", True),
        "created_at": user.get("created_at"),
    }
