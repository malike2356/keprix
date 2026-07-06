"""Document draft storage with Redis or in-memory fallback."""

from __future__ import annotations

import json
import os
import time
from typing import Any

from keprix.workspace.core.constants import DRAFT_TTL_SECONDS

_memory_drafts: dict[str, tuple[str, float]] = {}


class DraftStore:
    def _key(self, user_id: str, doc_id: str) -> str:
        return f"draft:{user_id}:{doc_id}"

    def save(self, user_id: str, doc_id: str, content: str) -> None:
        redis_url = os.getenv("REDIS_URL", "")
        key = self._key(user_id, doc_id)
        if redis_url:
            try:
                import redis

                client = redis.from_url(redis_url)
                client.setex(key, DRAFT_TTL_SECONDS, content)
                return
            except Exception:
                pass
        _memory_drafts[key] = (content, time.time() + DRAFT_TTL_SECONDS)

    def get(self, user_id: str, doc_id: str) -> str | None:
        redis_url = os.getenv("REDIS_URL", "")
        key = self._key(user_id, doc_id)
        if redis_url:
            try:
                import redis

                client = redis.from_url(redis_url)
                value = client.get(key)
                return value.decode("utf-8") if value else None
            except Exception:
                pass
        row = _memory_drafts.get(key)
        if not row:
            return None
        content, expires_at = row
        if time.time() > expires_at:
            _memory_drafts.pop(key, None)
            return None
        return content

    def delete(self, user_id: str, doc_id: str) -> None:
        redis_url = os.getenv("REDIS_URL", "")
        key = self._key(user_id, doc_id)
        if redis_url:
            try:
                import redis

                redis.from_url(redis_url).delete(key)
                return
            except Exception:
                pass
        _memory_drafts.pop(key, None)


draft_store = DraftStore()
