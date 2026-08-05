"""In-memory credential cache with TTL and zeroization."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable

from keprix.proxy.secret import Secret


def parse_duration_seconds(value: str | int | float | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = value.strip().lower()
    if not text:
        return 0.0
    unit = text[-1]
    number = float(text[:-1] if unit.isalpha() else text)
    if unit == "s" or not unit.isalpha():
        return number
    if unit == "m":
        return number * 60
    if unit == "h":
        return number * 3600
    if unit == "d":
        return number * 86400
    raise ValueError(f"Unsupported duration: {value}")


@dataclass
class CacheEntry:
    secret: Secret
    expires_at: float
    secret_hash: str

    def expired(self) -> bool:
        return time.time() >= self.expires_at

    def clear(self) -> None:
        self.secret.clear()


class CredentialCache:
    def __init__(self) -> None:
        self._entries: dict[str, CacheEntry] = {}

    def get(self, secret_ref: str, *, ttl_seconds: float, fetch: Callable[[], tuple[Secret, str]]) -> tuple[Secret, str, bool]:
        if ttl_seconds <= 0:
            secret, digest = fetch()
            return secret, digest, False
        entry = self._entries.get(secret_ref)
        if entry and not entry.expired():
            return Secret(entry.secret.expose()), entry.secret_hash, True
        if entry:
            entry.clear()
        secret, digest = fetch()
        self._entries[secret_ref] = CacheEntry(secret=Secret(secret.expose()), expires_at=time.time() + ttl_seconds, secret_hash=digest)
        return secret, digest, False

    def invalidate(self, secret_ref: str | None = None) -> int:
        refs = [secret_ref] if secret_ref else list(self._entries)
        count = 0
        for ref in refs:
            if ref is None:
                continue
            entry = self._entries.pop(ref, None)
            if entry:
                entry.clear()
                count += 1
        return count

    def size(self) -> int:
        return len(self._entries)
