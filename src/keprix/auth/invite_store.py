"""Persistent workspace user invites."""

from __future__ import annotations

import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir

INVITE_TTL_DAYS = 7


def _invites_path() -> Path:
    root = Path(data_dir())
    root.mkdir(parents=True, exist_ok=True)
    return root / "user_invites.json"


def _read() -> dict[str, Any]:
    path = _invites_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _write(data: dict[str, Any]) -> None:
    path = _invites_path()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _iso(dt: datetime | None = None) -> str:
    return (dt or datetime.now(timezone.utc)).isoformat()


def _is_expired(invite: dict[str, Any]) -> bool:
    expires = invite.get("expires_at")
    if not expires:
        return False
    try:
        return datetime.fromisoformat(str(expires)) <= datetime.now(timezone.utc)
    except ValueError:
        return False


class InviteStore:
    def list_all(self) -> list[dict[str, Any]]:
        return list(_read().values())

    def list_pending(self) -> list[dict[str, Any]]:
        rows = []
        for invite in self.list_all():
            if invite.get("status") != "pending":
                continue
            if _is_expired(invite):
                continue
            rows.append(invite)
        return rows

    def get(self, invite_id: str) -> dict[str, Any] | None:
        return _read().get(invite_id)

    def get_by_token(self, token: str) -> dict[str, Any] | None:
        for invite in self.list_all():
            if invite.get("token") == token:
                return invite
        return None

    def find_pending_by_email(self, email: str) -> dict[str, Any] | None:
        target = email.strip().lower()
        for invite in self.list_pending():
            if str(invite.get("email") or "").strip().lower() == target:
                return invite
        return None

    def create(
        self,
        *,
        email: str,
        role: str,
        invited_by: str,
        message: str | None = None,
        seat_id: str | None = None,
        owner_id: str | None = None,
    ) -> dict[str, Any]:
        data = _read()
        invite_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        row = {
            "id": invite_id,
            "token": secrets.token_urlsafe(32),
            "email": email.strip().lower(),
            "role": role,
            "message": message,
            "invited_by": invited_by,
            "seat_id": seat_id,
            "owner_id": owner_id,
            "status": "pending",
            "created_at": _iso(now),
            "expires_at": _iso(now + timedelta(days=INVITE_TTL_DAYS)),
            "accepted_at": None,
            "user_id": None,
        }
        data[invite_id] = row
        _write(data)
        return row

    def refresh_token(self, invite_id: str) -> dict[str, Any] | None:
        data = _read()
        invite = data.get(invite_id)
        if invite is None or invite.get("status") != "pending":
            return None
        now = datetime.now(timezone.utc)
        invite["token"] = secrets.token_urlsafe(32)
        invite["expires_at"] = _iso(now + timedelta(days=INVITE_TTL_DAYS))
        invite["updated_at"] = _iso(now)
        data[invite_id] = invite
        _write(data)
        return invite

    def mark_accepted(self, invite_id: str, user_id: str) -> dict[str, Any] | None:
        data = _read()
        invite = data.get(invite_id)
        if invite is None:
            return None
        invite["status"] = "accepted"
        invite["accepted_at"] = _iso()
        invite["user_id"] = user_id
        data[invite_id] = invite
        _write(data)
        return invite

    def revoke(self, invite_id: str) -> bool:
        data = _read()
        invite = data.get(invite_id)
        if invite is None:
            return False
        invite["status"] = "revoked"
        invite["revoked_at"] = _iso()
        data[invite_id] = invite
        _write(data)
        return True


invite_store = InviteStore()
