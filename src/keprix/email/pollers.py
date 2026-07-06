"""Background IMAP polling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from keprix.email.ai_pipeline import schedule_email_ai
from keprix.email.helpers import fetch_new_messages
from keprix.email.store import get_email_store

logger = logging.getLogger(__name__)

_poller_task: asyncio.Task[None] | None = None
_stop_event: asyncio.Event | None = None


async def _poll_account(account_conn: dict[str, Any], *, account_id: str, user_id: str) -> int:
    store = get_email_store()
    try:
        messages = await asyncio.to_thread(fetch_new_messages, account_conn)
    except Exception:
        logger.exception("IMAP poll failed for account %s", account_id)
        return 0
    new_count = 0
    account = await store.get_account(account_id, user_id)
    if account is None:
        return 0
    for parsed in messages:
        created = await store.upsert_email(account, parsed)
        if created:
            new_count += 1
            schedule_email_ai(created)
    await store.touch_polled(account_id)
    return new_count


async def _poll_loop() -> None:
    assert _stop_event is not None
    store = get_email_store()
    while not _stop_event.is_set():
        accounts = await store.list_active_accounts()
        for account in accounts:
            if _stop_event.is_set():
                break
            await _poll_account(account.to_connection(), account_id=account.id, user_id=account.user_id)
            interval = max(30, int(account.poll_interval_seconds))
            try:
                await asyncio.wait_for(_stop_event.wait(), timeout=min(interval, 60))
            except TimeoutError:
                pass
        else:
            try:
                await asyncio.wait_for(_stop_event.wait(), timeout=60)
            except TimeoutError:
                pass


def start_email_poller() -> asyncio.Task[None] | None:
    global _poller_task, _stop_event
    if _poller_task is not None and not _poller_task.done():
        return _poller_task
    _stop_event = asyncio.Event()
    _poller_task = asyncio.create_task(_poll_loop())
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
        accounts = [a for a in accounts if a.user_id == user_id]
    results: dict[str, int] = {}
    for account in accounts:
        count = await _poll_account(
            account.to_connection(), account_id=account.id, user_id=account.user_id
        )
        results[account.id] = count
    return results
