"""Background contact sync scheduler with durable sources and fail-closed updates."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.contacts.sync.base import ContactSyncConnector, SyncResult
from keprix.contacts.sync.carddav import CardDAVContactsConnector
from keprix.contacts.sync.google import GoogleContactsConnector
from keprix.contacts.sync.microsoft import MicrosoftContactsConnector

logger = logging.getLogger(__name__)

_connectors: dict[str, ContactSyncConnector] = {
    "google": GoogleContactsConnector(),
    "microsoft": MicrosoftContactsConnector(),
    "carddav": CardDAVContactsConnector(),
}

_sync_sources: dict[str, dict[str, Any]] = {}
_task: asyncio.Task[None] | None = None
_stop = asyncio.Event()
_lock = asyncio.Lock()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _persist(source: dict[str, Any]) -> None:
    from keprix.db.contacts_repo import pg_upsert_sync_source

    try:
        saved = await pg_upsert_sync_source(source)
        if saved is not None:
            _sync_sources[source["id"]] = {**source, **saved}
            return
    except Exception:
        logger.exception("Failed to persist contact sync source %s", source.get("id"))
    _sync_sources[source["id"]] = source


async def load_sync_sources_from_db() -> int:
    """Hydrate in-memory cache from Postgres after bootstrap."""
    from keprix.db.contacts_repo import pg_list_sync_sources

    rows = await pg_list_sync_sources(None)
    if rows is None:
        return 0
    async with _lock:
        for row in rows:
            _sync_sources[row["id"]] = row
    return len(rows)


async def register_sync_source(source: dict[str, Any]) -> dict[str, Any]:
    async with _lock:
        await _persist(source)
        return _sync_sources[source["id"]]


async def list_sync_sources(*, user_id: str | None = None) -> list[dict[str, Any]]:
    from keprix.db.contacts_repo import pg_list_sync_sources

    rows = await pg_list_sync_sources(user_id)
    if rows is not None:
        async with _lock:
            for row in rows:
                _sync_sources[row["id"]] = row
            if user_id is None:
                return list(_sync_sources.values())
            return [s for s in _sync_sources.values() if s.get("user_id") == user_id]
    async with _lock:
        if user_id is None:
            return list(_sync_sources.values())
        return [s for s in _sync_sources.values() if s.get("user_id") == user_id]


async def get_sync_source(
    source_id: str, *, user_id: str | None = None
) -> dict[str, Any] | None:
    from keprix.db.contacts_repo import pg_get_sync_source

    row = await pg_get_sync_source(source_id, user_id)
    if row is not None:
        async with _lock:
            _sync_sources[source_id] = row
        return row
    async with _lock:
        source = _sync_sources.get(source_id)
        if source is None:
            return None
        if user_id is not None and source.get("user_id") != user_id:
            return None
        return source


async def unregister_sync_source(source_id: str, *, user_id: str | None = None) -> bool:
    from keprix.db.contacts_repo import _use_db, pg_delete_sync_source

    if _use_db():
        deleted = await pg_delete_sync_source(source_id, user_id)
        if not deleted:
            return False
        async with _lock:
            _sync_sources.pop(source_id, None)
        return True
    async with _lock:
        existing = _sync_sources.get(source_id)
        if existing is None:
            return False
        if user_id is not None and existing.get("user_id") != user_id:
            return False
        _sync_sources.pop(source_id, None)
        return True


async def patch_sync_source(
    source_id: str, updates: dict[str, Any], *, user_id: str | None = None
) -> dict[str, Any] | None:
    source = await get_sync_source(source_id, user_id=user_id)
    if source is None:
        return None
    allowed = {"sync_enabled", "sync_interval_minutes", "display_name"}
    for key, value in updates.items():
        if key in allowed and value is not None:
            source[key] = value
    await _persist(source)
    return source


def _source_is_due(source: dict[str, Any], *, now: datetime | None = None) -> bool:
    if not source.get("sync_enabled", True):
        return False
    now = now or datetime.now(timezone.utc)
    last_raw = source.get("last_delta_sync_at") or source.get("last_full_sync_at")
    if not last_raw:
        return True
    try:
        last = datetime.fromisoformat(str(last_raw).replace("Z", "+00:00"))
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    minutes = max(5, int(source.get("sync_interval_minutes") or 60))
    return last + timedelta(minutes=minutes) <= now


async def run_sync(source_id: str) -> dict[str, Any]:
    source = await get_sync_source(source_id)
    if source is None:
        return {"error": "not found"}
    connector = _connectors.get(source["provider"])
    if connector is None:
        return {"error": "unknown provider"}
    try:
        if source.get("sync_token") or source.get("last_full_sync_at"):
            result = await connector.delta_sync(source)
        else:
            result = await connector.full_sync(source)
    except Exception as exc:
        logger.exception("Contact sync failed for %s", source_id)
        source["last_sync_error"] = str(exc)
        await _persist(source)
        return {"error": str(exc)}

    if not isinstance(result, SyncResult):
        source["last_sync_error"] = "invalid sync result"
        await _persist(source)
        return {"error": "invalid sync result"}

    if result.error:
        source["last_sync_error"] = result.error
        await _persist(source)
        return {"error": result.error, "added": result.added, "updated": result.updated}

    now = _utcnow_iso()
    if not source.get("last_full_sync_at"):
        source["last_full_sync_at"] = now
    source["last_delta_sync_at"] = now
    source["last_sync_error"] = None
    if result.sync_token:
        source["sync_token"] = result.sync_token
    try:
        from keprix.contacts.store import get_contact_store

        contacts = await get_contact_store().all_contacts(user_id=str(source.get("user_id") or "local"))
        provider = source.get("provider")
        source["contact_count"] = sum(1 for c in contacts if c.source == provider)
    except Exception:
        source["contact_count"] = int(source.get("contact_count") or 0) + int(result.added)
    await _persist(source)
    return {
        "added": result.added,
        "updated": result.updated,
        "skipped": result.skipped,
        "sync_token": result.sync_token,
    }


async def _loop() -> None:
    while not _stop.is_set():
        async with _lock:
            due_ids = [sid for sid, src in _sync_sources.items() if _source_is_due(src)]
        for source_id in due_ids:
            await run_sync(source_id)
        try:
            await asyncio.wait_for(_stop.wait(), timeout=60)
        except TimeoutError:
            pass


def start_contact_sync_scheduler() -> None:
    global _task
    if _task is None or _task.done():
        _stop.clear()
        _task = asyncio.create_task(_loop())


async def stop_contact_sync_scheduler() -> None:
    _stop.set()
    if _task is not None:
        try:
            await asyncio.wait_for(_task, timeout=5)
        except TimeoutError:
            _task.cancel()


def reset_sync_sources_for_tests() -> None:
    _sync_sources.clear()
