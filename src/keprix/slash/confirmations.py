"""Confirmation tokens for risky slash commands."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable

DEFAULT_TTL_SECONDS = 600


@dataclass
class PendingSlash:
    token_hash: str
    command: str
    context: dict[str, Any]
    user_id: str
    workspace_id: str
    role: str
    preview: str
    risk_level: str
    created_at: datetime
    expires_at: datetime
    executed: bool = False
    handler: Callable[[], Awaitable[Any]] | None = None


class SlashConfirmationStore:
    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._by_token: dict[str, PendingSlash] = {}
        self._by_hash: dict[str, str] = {}

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create(
        self,
        *,
        command: str,
        context: dict[str, Any],
        user_id: str,
        workspace_id: str,
        role: str,
        preview: str,
        risk_level: str,
        handler: Callable[[], Awaitable[Any]] | None = None,
    ) -> tuple[str, str]:
        token = secrets.token_urlsafe(12)
        token_hash = self._hash(token)
        now = datetime.now(timezone.utc)
        pending = PendingSlash(
            token_hash=token_hash,
            command=command,
            context=context,
            user_id=user_id,
            workspace_id=workspace_id,
            role=role,
            preview=preview,
            risk_level=risk_level,
            created_at=now,
            expires_at=now + timedelta(seconds=self._ttl),
            handler=handler,
        )
        pending_id = str(uuid.uuid4())
        self._by_token[pending_id] = pending
        self._by_hash[token_hash] = pending_id
        return token, token_hash

    def get(self, token: str) -> PendingSlash | None:
        token_hash = self._hash(token)
        pending_id = self._by_hash.get(token_hash)
        if not pending_id:
            return None
        pending = self._by_token.get(pending_id)
        if not pending:
            return None
        if pending.expires_at < datetime.now(timezone.utc):
            self.cancel(token)
            return None
        return pending

    def cancel(self, token: str) -> bool:
        token_hash = self._hash(token)
        pending_id = self._by_hash.pop(token_hash, None)
        if not pending_id:
            return False
        self._by_token.pop(pending_id, None)
        return True

    def mark_executed(self, token: str) -> None:
        pending = self.get(token)
        if pending:
            pending.executed = True


_store: SlashConfirmationStore | None = None


def get_confirmation_store() -> SlashConfirmationStore:
    global _store
    if _store is None:
        _store = SlashConfirmationStore()
    return _store


class CyberAuthorizationStore:
    """Active authorization records for cyber-scoped slash commands."""

    def __init__(self) -> None:
        self._active: set[tuple[str, str]] = set()

    def grant(self, workspace_id: str, user_id: str) -> None:
        self._active.add((workspace_id, user_id))

    def is_active(self, workspace_id: str, user_id: str) -> bool:
        return (workspace_id, user_id) in self._active


_cyber_store: CyberAuthorizationStore | None = None


def get_cyber_authorization_store() -> CyberAuthorizationStore:
    global _cyber_store
    if _cyber_store is None:
        _cyber_store = CyberAuthorizationStore()
    return _cyber_store
