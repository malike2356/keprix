"""Short-lived step-up verification tokens after email OTP."""

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

STEP_UP_TTL_SECONDS = 300


def _tokens_path() -> Path:
    root = Path(data_dir())
    root.mkdir(parents=True, exist_ok=True)
    return root / "step_up_tokens.json"


class StepUpStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()

    def _read(self) -> dict[str, Any]:
        path = _tokens_path()
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
        now = time.time()
        pruned = {
            token_id: record
            for token_id, record in data.items()
            if record.get("expires_at", 0) > now and record.get("used_at") is None
        }
        if len(pruned) != len(data):
            self._write(pruned)
        return pruned

    def _write(self, data: dict[str, Any]) -> None:
        path = _tokens_path()
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def issue(self, user_id: str, *, ttl_seconds: int = STEP_UP_TTL_SECONDS) -> str:
        raw = secrets.token_urlsafe(32)
        token_id = str(uuid.uuid4())
        now = time.time()
        record = {
            "id": token_id,
            "user_id": user_id,
            "token_hash": hash_token(raw),
            "expires_at": now + ttl_seconds,
            "used_at": None,
            "created_at": now,
        }
        with self._lock:
            data = self._read()
            data[token_id] = record
            self._write(data)
        return raw

    def consume(self, user_id: str, raw_token: str) -> bool:
        if not raw_token.strip():
            return False
        target_hash = hash_token(raw_token.strip())
        now = time.time()
        with self._lock:
            data = self._read()
            for token_id, record in data.items():
                if record.get("user_id") != user_id:
                    continue
                if record.get("token_hash") != target_hash:
                    continue
                if record.get("used_at") is not None:
                    return False
                if record.get("expires_at", 0) <= now:
                    return False
                record["used_at"] = now
                data[token_id] = record
                self._write(data)
                return True
        return False


step_up_store = StepUpStore()
