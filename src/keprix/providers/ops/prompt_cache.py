"""Prompt cache: deduplicate identical system prompts across requests."""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class CacheEntry:
    key: str
    messages: list[dict[str, Any]]
    response: Any
    created_at: float = field(default_factory=time.monotonic)
    hits: int = 0
    tokens_saved: int = 0


class PromptCache:
    """Cache identical or near-identical prompts to avoid redundant LLM calls.

    Uses a SHA-256 digest of the canonical JSON of the message list as
    the cache key. TTL-based expiry prevents serving stale responses.

    Primarily useful for:
      - Identical classification prompts sent repeatedly
      - System prompt + fixed few-shots with variable user turn

    Usage::

        cache = PromptCache(ttl=300)
        key = cache.make_key(messages)
        if (hit := cache.get(key)):
            return hit.response
        response = await call_llm(messages)
        cache.put(key, messages, response, tokens_saved=estimated)
    """

    def __init__(self, ttl: float = 300.0, max_size: int = 512) -> None:
        self._ttl = ttl
        self._max = max_size
        self._store: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    def make_key(self, messages: list[dict[str, Any]]) -> str:
        canonical = json.dumps(messages, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode()).hexdigest()[:32]

    async def get(self, key: str) -> CacheEntry | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if time.monotonic() - entry.created_at > self._ttl:
                del self._store[key]
                return None
            entry.hits += 1
            return entry

    async def put(
        self,
        key: str,
        messages: list[dict[str, Any]],
        response: Any,
        tokens_saved: int = 0,
    ) -> None:
        async with self._lock:
            if len(self._store) >= self._max:
                # Evict oldest entry
                oldest = min(self._store, key=lambda k: self._store[k].created_at)
                del self._store[oldest]
            self._store[key] = CacheEntry(
                key=key,
                messages=messages,
                response=response,
                tokens_saved=tokens_saved,
            )

    async def invalidate(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def purge_expired(self) -> int:
        now = time.monotonic()
        async with self._lock:
            expired = [k for k, e in self._store.items() if now - e.created_at > self._ttl]
            for k in expired:
                del self._store[k]
        return len(expired)

    async def stats(self) -> dict[str, Any]:
        async with self._lock:
            entries = list(self._store.values())
        return {
            "size": len(entries),
            "total_hits": sum(e.hits for e in entries),
            "total_tokens_saved": sum(e.tokens_saved for e in entries),
        }
