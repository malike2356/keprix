"""Background IMAP polling with per-account intervals."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from keprix.email.ai_pipeline import schedule_email_ai
from keprix.email.helpers import fetch_new_messages, resolve_account_connection
from keprix.email.store import get_email_store

logger = logging.getLogger(__name__)

_poller_task: asyncio.Task[None] | None = None
_stop_event: asyncio.Event | None = None
DEFAULT_TICK_SECONDS = 30
MIN_INTERVAL_SECONDS = 30


def _as_aware(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


def account_is_due(account: Any, *, now: datetime | None = None) -> bool:
    if not getattr(account, "is_active", True):
        return False
    now = now or datetime.now(timezone.utc)
    last = _as_aware(getattr(account, "last_polled_at", None))
    if last is None:
        return True
    interval = max(MIN_INTERVAL_SECONDS, int(getattr(account, "poll_interval_seconds", 60) or 60))
    return last + timedelta(seconds=interval) <= now


async def _poll_account(account: Any) -> int:
    store = get_email_store()
    try:
        account_conn = await resolve_account_connection(account)
        messages = await asyncio.to_thread(fetch_new_messages, account_conn)
    except Exception:
        logger.exception("IMAP poll failed for account %s", getattr(account, "id", "?"))
        return 0
    new_count = 0
    refreshed = await store.get_account(account.id, account.user_id)
    if refreshed is None:
        return 0
    for parsed in messages:
        created = await store.upsert_email(refreshed, parsed)
        if created:
            new_count += 1
            schedule_email_ai(created)
    await store.touch_polled(account.id)
    return new_count


async def _poll_loop() -> None:
    assert _stop_event is not None
    store = get_email_store()
    while not _stop_event.is_set():
        try:
            accounts = await store.list_active_accounts()
            for account in accounts:
                if _stop_event.is_set():
                    break
                if not account_is_due(account):
                    continue
                await _poll_account(account)
        except Exception:
            logger.exception("email poll loop iteration failed")
        try:
            await asyncio.wait_for(_stop_event.wait(), timeout=DEFAULT_TICK_SECONDS)
        except TimeoutError:
            pass


def start_email_poller() -> asyncio.Task[None] | None:
    global _poller_task, _stop_event
    if _poller_task is not None and not _poller_task.done():
        return _poller_task
    _stop_event = asyncio.Event()
    _poller_task = asyncio.create_task(_poll_loop(), name="keprix-email-poller")
    return _poller_task


async def stop_email_poller() -> None:
    global _poller_task, _stop_event
    if _stop_event is not None:
        _stop_event.set()
    if _poller_task is not None:
        try:
            await asyncio.wait_for(_poller_task, timeout=5)
        except TimeoutError:
            _poller_task.cancel()
        _poller_task = None
    _stop_event = None


async def sync_all_accounts(user_id: str | None = None) -> dict[str, int]:
    store = get_email_store()
    accounts = await store.list_active_accounts()
    if user_id:
        accounts = [account for account in accounts if account.user_id == user_id]
    synced = 0
    errors = 0
    for account in accounts:
        try:
            synced += await _poll_account(account)
        except Exception:
            errors += 1
            logger.exception("manual email sync failed for %s", account.id)
    return {"synced": synced, "errors": errors, "accounts": len(accounts)}
