"""Background contact sync scheduler."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from keprix.contacts.sync.base import ContactSyncConnector
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


async def register_sync_source(source: dict[str, Any]) -> None:
    _sync_sources[source["id"]] = source


async def list_sync_sources() -> list[dict[str, Any]]:
    return list(_sync_sources.values())


async def get_sync_source(source_id: str) -> dict[str, Any] | None:
    return _sync_sources.get(source_id)


async def run_sync(source_id: str) -> dict[str, Any]:
    source = _sync_sources.get(source_id)
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
        source["last_full_sync_at"] = source.get("last_full_sync_at") or datetime.now(timezone.utc).isoformat()
        source["last_delta_sync_at"] = datetime.now(timezone.utc).isoformat()
        source["last_sync_error"] = None
        if result.sync_token:
            source["sync_token"] = result.sync_token
        source["contact_count"] = result.added + result.updated + int(source.get("contact_count") or 0)
        _sync_sources[source_id] = source
        return {
            "added": result.added,
            "updated": result.updated,
            "skipped": result.skipped,
        }
    except Exception as exc:
        logger.exception("Contact sync failed for %s", source_id)
        source["last_sync_error"] = str(exc)
        _sync_sources[source_id] = source
        return {"error": str(exc)}


async def _loop() -> None:
    while not _stop.is_set():
        for source_id, source in list(_sync_sources.items()):
            if not source.get("sync_enabled", True):
                continue
            await run_sync(source_id)
        try:
            await asyncio.wait_for(_stop.wait(), timeout=300)
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
