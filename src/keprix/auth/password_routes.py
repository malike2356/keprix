"""Password change and reset routes."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.auth.dependencies import get_current_user
from keprix.auth.password_reset import password_reset_url, send_password_reset_email
from keprix.auth.password_reset_store import password_reset_store
from keprix.auth.routes import _public_user
from keprix.auth.session import auth_manager
from keprix.security.audit import audit_log
from keprix.security.rate_limiter import rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth-password"])

FORGOT_SUCCESS_MESSAGE = "If an account exists, a reset link was sent."


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class ForgotPasswordRequest(BaseModel):
    email_or_username: str = Field(..., min_length=1, max_length=320)


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=8)
    new_password: str = Field(..., min_length=8)


@router.post("/me/password")
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    ok, message = auth_manager.change_password(str(user["id"]), body.current_password, body.new_password)
    if not ok:
        status = 401 if message == "Invalid current password" else 400
        raise HTTPException(status_code=status, detail=message)

    current_token = getattr(request.state, "auth_token", None)
    auth_manager.revoke_other_sessions(str(user["username"]), keep_token=current_token)

    await audit_log(
        "password_changed",
        user_id=user.get("id"),
        ip_address=request.client.host if request.client else None,
    )
    return {"ok": True, "message": message}


@router.post("/password/forgot")
async def forgot_password(body: ForgotPasswordRequest, request: Request) -> dict[str, Any]:
    client_ip = request.client.host if request.client else "unknown"
    if not rate_limit("auth_password_forgot", client_ip, limit=3, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Too many reset requests", headers={"Retry-After": "3600"})

    login = body.email_or_username.strip()
    matched = auth_manager._find_user_by_login(login)
    if matched:
        user_id = str(matched["id"])
        email = str(matched.get("email") or "").strip().lower()
        if email:
            raw_token = password_reset_store.create_reset_token(user_id)
            reset_url = password_reset_url(raw_token)
            await send_password_reset_email(to_email=email, reset_url=reset_url, user_id=user_id)
            await audit_log(
                "password_reset_requested",
                user_id=user_id,
                ip_address=client_ip,
                event_data={"email_sent_target": True},
            )
        else:
            await audit_log(
                "password_reset_requested",
                user_id=user_id,
                ip_address=client_ip,
                event_data={"email_sent_target": False},
            )

    return {"ok": True, "message": FORGOT_SUCCESS_MESSAGE}


@router.post("/password/reset")
async def reset_password(body: ResetPasswordRequest, request: Request) -> dict[str, Any]:
    user_id = password_reset_store.consume_reset_token(body.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    try:
        auth_manager.reset_password(user_id, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user = auth_manager.get_user_by_id(user_id)
    if user:
        auth_manager.revoke_other_sessions(str(user["username"]))

    await audit_log(
        "password_reset_completed",
        user_id=user_id,
        ip_address=request.client.host if request.client else None,
    )
    return {
        "ok": True,
        "message": "Password reset. You can sign in with your new password.",
        "user": _public_user(user) if user else None,
    }
