"""Persistent password reset tokens."""

from __future__ import annotations

import json
import secrets
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir
from keprix.security.crypto import hash_token

DEFAULT_TTL_HOURS = 1


def _tokens_path() -> Path:
    root = Path(data_dir())
    root.mkdir(parents=True, exist_ok=True)
    return root / "password_reset_tokens.json"


class PasswordResetStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()

    def _read(self) -> dict[str, Any]:
        path = _tokens_path()
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write(self, data: dict[str, Any]) -> None:
        path = _tokens_path()
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def invalidate_user_tokens(self, user_id: str) -> None:
        with self._lock:
            data = self._read()
            changed = False
            now = time.time()
            for record in data.values():
                if record.get("user_id") != user_id:
                    continue
                if record.get("used_at") is not None:
                    continue
                record["used_at"] = now
                changed = True
            if changed:
                self._write(data)

    def create_reset_token(self, user_id: str, *, ttl_hours: int = DEFAULT_TTL_HOURS) -> str:
        self.invalidate_user_tokens(user_id)
        raw = secrets.token_urlsafe(32)
        token_id = str(uuid.uuid4())
        now = time.time()
        record = {
            "id": token_id,
            "user_id": user_id,
            "token_hash": hash_token(raw),
            "expires_at": now + ttl_hours * 3600,
            "used_at": None,
            "created_at": now,
        }
        with self._lock:
            data = self._read()
            data[token_id] = record
            self._write(data)
        return raw

    def consume_reset_token(self, raw_token: str) -> str | None:
        if not raw_token.strip():
            return None
        target_hash = hash_token(raw_token.strip())
        now = time.time()
        with self._lock:
            data = self._read()
            for token_id, record in data.items():
                if record.get("token_hash") != target_hash:
                    continue
                if record.get("used_at") is not None:
                    return None
                if record.get("expires_at", 0) <= now:
                    return None
                user_id = str(record.get("user_id") or "")
                if not user_id:
                    return None
                record["used_at"] = now
                data[token_id] = record
                self._write(data)
                return user_id
        return None


password_reset_store = PasswordResetStore()
