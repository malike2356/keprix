"""Workspace user invite and accept flows."""

from __future__ import annotations

import logging
import os
import re
from typing import Any

from keprix.auth.invite_store import invite_store
from keprix.auth.session import auth_manager
from keprix.security.audit import audit_log

logger = logging.getLogger(__name__)


class InviteError(ValueError):
    pass


def instance_frontend_url() -> str:
    return os.environ.get("KEPRIX_INSTANCE_URL", "http://localhost:3000").rstrip("/")


def _username_from_email(email: str) -> str:
    local = email.split("@", 1)[0].strip().lower()
    local = re.sub(r"[^a-z0-9._-]+", "", local)
    return local or "user"


def _find_user_by_email(email: str) -> dict[str, Any] | None:
    target = email.strip().lower()
    for user in auth_manager.users.values():
        if str(user.get("email") or "").strip().lower() == target:
            return user
    return None


def _public_invite(invite: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": invite.get("id"),
        "email": invite.get("email"),
        "role": invite.get("role"),
        "message": invite.get("message"),
        "status": invite.get("status"),
        "expires_at": invite.get("expires_at"),
        "created_at": invite.get("created_at"),
        "seat_id": invite.get("seat_id"),
    }


def invite_accept_url(token: str) -> str:
    return f"{instance_frontend_url()}/auth/accept-invite?token={token}"


async def send_workspace_invite(
    *,
    email: str,
    role: str,
    invited_by: str,
    message: str | None = None,
    seat_id: str | None = None,
    owner_id: str | None = None,
) -> dict[str, Any]:
    normalized_email = email.strip().lower()
    if not normalized_email or "@" not in normalized_email:
        raise InviteError("Valid email is required")

    existing = _find_user_by_email(normalized_email)
    if existing and existing.get("is_active", True) and existing.get("is_approved", True):
        raise InviteError("A user with this email already exists")

    pending = invite_store.find_pending_by_email(normalized_email)
    if pending:
        invite = invite_store.refresh_token(pending["id"]) or pending
    else:
        invite = invite_store.create(
            email=normalized_email,
            role=role,
            invited_by=invited_by,
            message=message,
            seat_id=seat_id,
            owner_id=owner_id,
        )

    accept_url = invite_accept_url(str(invite["token"]))
    email_sent = await _send_invite_email(
        to_email=normalized_email,
        accept_url=accept_url,
        role=role,
        message=message,
        invited_by=invited_by,
        invite_id=str(invite["id"]),
    )

    await audit_log(
        "workspace_user_invited",
        user_id=invited_by,
        event_data={"invite_id": invite["id"], "email": normalized_email, "email_sent": email_sent},
    )

    return {
        "invite": _public_invite(invite),
        "invite_url": accept_url,
        "email_sent": email_sent,
    }


async def resend_workspace_invite(invite_id: str, *, invited_by: str) -> dict[str, Any]:
    invite = invite_store.get(invite_id)
    if invite is None or invite.get("status") != "pending":
        raise InviteError("Invite not found or no longer pending")

    refreshed = invite_store.refresh_token(invite_id) or invite
    accept_url = invite_accept_url(str(refreshed["token"]))
    email_sent = await _send_invite_email(
        to_email=str(refreshed["email"]),
        accept_url=accept_url,
        role=str(refreshed.get("role") or "user"),
        message=refreshed.get("message"),
        invited_by=invited_by,
        invite_id=invite_id,
    )
    return {"invite": _public_invite(refreshed), "invite_url": accept_url, "email_sent": email_sent}


def get_invite_preview(token: str) -> dict[str, Any]:
    invite = invite_store.get_by_token(token)
    if invite is None:
        raise InviteError("Invite not found")
    if invite.get("status") != "pending":
        raise InviteError("Invite is no longer valid")
    expires_at = invite.get("expires_at")
    if expires_at:
        from datetime import datetime, timezone

        try:
            if datetime.fromisoformat(str(expires_at)) <= datetime.now(timezone.utc):
                raise InviteError("Invite has expired")
        except ValueError:
            pass
    return _public_invite(invite)


async def accept_workspace_invite(
    token: str,
    password: str,
    *,
    username: str | None = None,
) -> dict[str, Any]:
    if len(password) < 8:
        raise InviteError("Password must be at least 8 characters")

    invite = invite_store.get_by_token(token)
    if invite is None:
        raise InviteError("Invite not found")
    if invite.get("status") != "pending":
        raise InviteError("Invite is no longer valid")

    preview = get_invite_preview(token)
    email = str(invite["email"])
    role = str(invite.get("role") or "user")
    user_key = (username or _username_from_email(email)).strip().lower()

    existing = _find_user_by_email(email)
    if existing:
        user = auth_manager.set_password_and_approve(str(existing["id"]), password, role=role)
        if user is None:
            raise InviteError("Unable to activate existing user")
    else:
        base_key = user_key
        suffix = 1
        while auth_manager.get_user(user_key):
            user_key = f"{base_key}{suffix}"
            suffix += 1
        try:
            user = auth_manager.create_user(
                user_key,
                password,
                role=role,
                email=email,
                is_approved=True,
            )
        except ValueError as exc:
            raise InviteError(str(exc)) from exc

    invite_store.mark_accepted(str(invite["id"]), str(user["id"]))
    seat_id = invite.get("seat_id")
    if seat_id:
        await _activate_billing_seat(str(seat_id), str(user["id"]), email)

    session_token = auth_manager.create_session(str(user["username"]))
    await audit_log(
        "workspace_user_invite_accepted",
        user_id=user.get("id"),
        event_data={"invite_id": invite["id"], "seat_id": seat_id},
    )

    return {
        "token": session_token,
        "user": {
            "id": user.get("id"),
            "username": user.get("username"),
            "email": user.get("email"),
            "role": user.get("role", "user"),
        },
        "invite": preview,
    }


async def _activate_billing_seat(seat_id: str, user_id: str, email: str) -> None:
    from keprix.billing.store import get_billing_store

    await get_billing_store().update_seat(
        seat_id,
        {"status": "active", "user_id": user_id, "email": email},
    )


async def _send_invite_email(
    *,
    to_email: str,
    accept_url: str,
    role: str,
    message: str | None,
    invited_by: str,
    invite_id: str,
) -> bool:
    subject = "You are invited to Keprix"
    custom = f"\n\n{message.strip()}\n" if message and message.strip() else ""
    body_text = (
        f"You have been invited to join a Keprix workspace as {role}.{custom}\n"
        f"Accept your invite and set your password:\n{accept_url}\n\n"
        "This link expires in 7 days."
    )
    body_html = (
        f"<p>You have been invited to join a Keprix workspace as <strong>{role}</strong>.</p>"
        f"{f'<p>{message}</p>' if message else ''}"
        f'<p><a href="{accept_url}">Accept invite and set your password</a></p>'
        "<p>This link expires in 7 days.</p>"
    )
    try:
        from keprix.notify_external.smtp_sender import SMTPNotConfigured, send_email

        await send_email(
            "default",
            to_email,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            triggered_by="workspace_invite",
            triggered_by_id=invite_id,
        )
        return True
    except SMTPNotConfigured:
        logger.info("SMTP not configured; invite link for %s: %s", to_email, accept_url)
        return False
    except Exception as exc:
        logger.warning("Failed to send invite email to %s: %s", to_email, exc)
        return False


def workspace_user_row(user: dict[str, Any]) -> dict[str, Any]:
    if not user.get("is_approved", True):
        status = "invited"
    elif not user.get("is_active", True):
        status = "suspended"
    else:
        status = "active"
    return {
        "id": user.get("id"),
        "name": user.get("username"),
        "email": user.get("email") or f"{user.get('username')}@local",
        "role": user.get("role", "user"),
        "status": status,
        "joined_at": user.get("created_at"),
        "last_active_at": user.get("last_login_at"),
        "source": "account",
    }


def pending_invite_row(invite: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": invite.get("id"),
        "name": invite.get("email", "").split("@", 1)[0],
        "email": invite.get("email"),
        "role": invite.get("role", "user"),
        "status": "invited",
        "joined_at": None,
        "last_active_at": None,
        "source": "invite",
        "invite_id": invite.get("id"),
        "expires_at": invite.get("expires_at"),
    }
