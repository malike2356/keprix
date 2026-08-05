"""Email OTP send and verify routes."""

from __future__ import annotations

import time
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from keprix.auth.config import otp_login_enabled, otp_step_up_enabled, otp_ttl_minutes
from keprix.auth.dependencies import get_optional_current_user
from keprix.auth.otp_email import send_otp_email
from keprix.auth.otp_store import otp_store
from keprix.auth.request_context import client_ip as resolve_client_ip, client_label
from keprix.auth.routes import _public_user
from keprix.auth.session import auth_manager
from keprix.auth.step_up_store import STEP_UP_TTL_SECONDS, step_up_store
from keprix.security.audit import audit_log
from keprix.security.rate_limiter import rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth-otp"])

OTP_SEND_SUCCESS = "If an account exists, a verification code was sent."


class OtpSendRequest(BaseModel):
    email_or_username: str | None = Field(None, max_length=320)
    purpose: Literal["login", "step_up"] = "login"


class OtpVerifyRequest(BaseModel):
    challenge_id: str
    code: str = Field(..., min_length=6, max_length=6)


@router.post("/otp/send")
async def otp_send(
    body: OtpSendRequest,
    request: Request,
    user: dict | None = Depends(get_optional_current_user),
) -> dict[str, Any]:
    ip = resolve_client_ip(request)
    if not rate_limit("auth_otp_send", ip, limit=5, window_seconds=3600):
        raise HTTPException(status_code=429, detail="Too many OTP requests", headers={"Retry-After": "3600"})

    purpose = body.purpose
    if purpose == "login":
        if not otp_login_enabled():
            raise HTTPException(status_code=403, detail="Email OTP login is disabled")
        login = (body.email_or_username or "").strip()
        if not login:
            raise HTTPException(status_code=400, detail="Email or username is required")
        matched = auth_manager._find_user_by_login(login)
        if not matched:
            return {"ok": True, "message": OTP_SEND_SUCCESS}
        user_id = str(matched["id"])
        email = str(matched.get("email") or "").strip().lower()
        if not email:
            return {"ok": True, "message": OTP_SEND_SUCCESS}
    else:
        if not otp_step_up_enabled():
            raise HTTPException(status_code=403, detail="Email OTP step-up is disabled")
        if user is None:
            raise HTTPException(status_code=401, detail="Authentication required")
        user_id = str(user["id"])
        email = str(user.get("email") or "").strip().lower()
        if not email:
            raise HTTPException(status_code=400, detail="Add an email address to your profile before using email OTP")

    ttl = otp_ttl_minutes()
    challenge_id, code = otp_store.create_otp(user_id, purpose, ttl_minutes=ttl)
    await send_otp_email(
        to_email=email,
        code=code,
        purpose=purpose,
        user_id=user_id,
        ttl_minutes=ttl,
        ip_address=ip,
    )
    await audit_log(
        "otp_sent",
        user_id=user_id,
        ip_address=ip,
        event_data={"purpose": purpose},
    )
    return {
        "ok": True,
        "message": OTP_SEND_SUCCESS,
        "challenge_id": challenge_id,
        "expires_in_minutes": ttl,
    }


@router.post("/otp/verify")
async def otp_verify(body: OtpVerifyRequest, request: Request) -> dict[str, Any]:
    ip = resolve_client_ip(request)
    if not rate_limit("auth_otp_verify", ip, limit=10, window_seconds=600):
        raise HTTPException(status_code=429, detail="Too many OTP attempts", headers={"Retry-After": "600"})

    verified = otp_store.verify_otp(body.challenge_id, body.code)
    if not verified:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    user_id, purpose = verified
    user = auth_manager.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification code")

    if purpose == "login":
        if not otp_login_enabled():
            raise HTTPException(status_code=403, detail="Email OTP login is disabled")
        token = auth_manager.create_session(
            str(user["username"]),
            device_label=client_label(request),
            ip_address=ip,
        )
        user["last_login_at"] = time.time()
        auth_manager._save()
        await audit_log("login", user_id=user_id, ip_address=ip, event_data={"method": "email_otp"})
        return {"token": token, "user": _public_user(user)}

    if purpose == "step_up":
        if not otp_step_up_enabled():
            raise HTTPException(status_code=403, detail="Email OTP step-up is disabled")
        step_up_token = step_up_store.issue(user_id)
        await audit_log("otp_step_up_verified", user_id=user_id, ip_address=ip)
        return {"step_up_token": step_up_token, "expires_in": STEP_UP_TTL_SECONDS}

    raise HTTPException(status_code=400, detail="Unsupported OTP purpose")
