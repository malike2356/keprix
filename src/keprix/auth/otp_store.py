"""Email OTP challenge storage."""

from __future__ import annotations

import json
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from keprix.auth.config import data_dir, otp_ttl_minutes
from keprix.security.crypto import hash_token

MAX_ATTEMPTS = 5
VALID_PURPOSES = frozenset({"login", "step_up", "password_reset_fallback"})


def _challenges_path() -> Path:
    root = Path(data_dir())
    root.mkdir(parents=True, exist_ok=True)
    return root / "otp_challenges.json"


@dataclass
class OtpChallenge:
    id: str
    user_id: str
    purpose: str
    code_hash: str
    expires_at: float
    attempts: int


class OtpStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()

    def _read(self) -> dict[str, Any]:
        path = _challenges_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        now = time.time()
        pruned = {
            challenge_id: record
            for challenge_id, record in data.items()
            if record.get("expires_at", 0) > now and record.get("used_at") is None
        }
        if len(pruned) != len(data):
            self._write(pruned)
        return pruned

    def _write(self, data: dict[str, Any]) -> None:
        path = _challenges_path()
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def invalidate_user_challenges(self, user_id: str, *, purpose: str | None = None) -> None:
        with self._lock:
            data = self._read()
            changed = False
            now = time.time()
            for record in data.values():
                if record.get("user_id") != user_id:
                    continue
                if purpose and record.get("purpose") != purpose:
                    continue
                if record.get("used_at") is not None:
                    continue
                record["used_at"] = now
                changed = True
            if changed:
                self._write(data)

    def create_otp(self, user_id: str, purpose: str, *, ttl_minutes: int | None = None) -> tuple[str, str]:
        if purpose not in VALID_PURPOSES:
            raise ValueError("Invalid OTP purpose")
        ttl = ttl_minutes if ttl_minutes is not None else otp_ttl_minutes()
        self.invalidate_user_challenges(user_id, purpose=purpose)
        plain_code = f"{secrets.randbelow(1_000_000):06d}"
        challenge_id = str(uuid.uuid4())
        now = time.time()
        record = {
            "id": challenge_id,
            "user_id": user_id,
            "purpose": purpose,
            "code_hash": hash_token(plain_code),
            "expires_at": now + ttl * 60,
            "attempts": 0,
            "used_at": None,
            "created_at": now,
        }
        with self._lock:
            data = self._read()
            data[challenge_id] = record
            self._write(data)
        return challenge_id, plain_code

    def verify_otp(self, challenge_id: str, code: str, *, max_attempts: int = MAX_ATTEMPTS) -> tuple[str, str] | None:
        normalized = code.strip()
        if not normalized.isdigit() or len(normalized) != 6:
            return None
        target_hash = hash_token(normalized)
        now = time.time()
        with self._lock:
            data = self._read()
            record = data.get(challenge_id)
            if not record:
                return None
            if record.get("used_at") is not None:
                return None
            if record.get("expires_at", 0) <= now:
                return None
            attempts = int(record.get("attempts") or 0)
            if attempts >= max_attempts:
                return None
            if record.get("code_hash") != target_hash:
                record["attempts"] = attempts + 1
                data[challenge_id] = record
                self._write(data)
                return None
            user_id = str(record.get("user_id") or "")
            purpose = str(record.get("purpose") or "")
            if not user_id or purpose not in VALID_PURPOSES:
                return None
            record["used_at"] = now
            data[challenge_id] = record
            self._write(data)
            return user_id, purpose


otp_store = OtpStore()
