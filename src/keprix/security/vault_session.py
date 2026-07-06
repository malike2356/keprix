"""In-memory vault session keys (never persisted)."""

from __future__ import annotations

import threading
from typing import Any


class VaultSessionManager:
    """Keeps derived vault keys only in process memory."""

    def __init__(self) -> None:
        self._keys: dict[str, bytes] = {}
        self._lock = threading.Lock()

    def unlock(self, user_id: str, key: bytes) -> None:
        with self._lock:
            self._keys[user_id] = key

    def is_unlocked(self, user_id: str) -> bool:
        with self._lock:
            return user_id in self._keys

    def get_key(self, user_id: str) -> bytes | None:
        with self._lock:
            return self._keys.get(user_id)

    def lock(self, user_id: str) -> None:
        with self._lock:
            key = self._keys.pop(user_id, None)
            if key is not None:
                mutable = bytearray(key)
                for idx in range(len(mutable)):
                    mutable[idx] = 0

    def lock_all(self) -> None:
        with self._lock:
            for user_id in list(self._keys.keys()):
                self.lock(user_id)


vault_sessions = VaultSessionManager()
