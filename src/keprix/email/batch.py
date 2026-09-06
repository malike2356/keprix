"""Approval-gated, opt-out-aware email batch orchestration."""

from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Any

from keprix.crm.store import get_crm_store
from keprix.email.approval_gate import find_approved_approval, is_loopback_trusted, request_approval, require_approval, record_sent
from keprix.email.helpers import resolve_account_connection, send_smtp_message
from keprix.email.store import EmailBatchRecord, get_email_store


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def build_batch(user_id: str, *, name: str, lead_ids: list[str], subject: str, body: str) -> EmailBatchRecord:
    crm = get_crm_store()
    seen: set[str] = set()
    sends: list[dict[str, Any]] = []
    for lead_id in list(dict.fromkeys(str(x) for x in lead_ids))[:500]:
        lead = crm.get_lead(user_id, lead_id)
        if not lead:
            continue
        for item in lead.get("emails") or []:
            address = str(item.get("address") if isinstance(item, dict) else item).strip().lower()
            if not address or address in seen:
                continue
            seen.add(address)
            if crm.is_suppressed(user_id, channel="email", address=address):
                sends.append({"lead_id": lead_id, "recipient": address, "subject": subject, "body": body, "status": "skipped_opted_out"})
            else:
                sends.append({"lead_id": lead_id, "recipient": address, "subject": subject, "body": body})
            break
    return await get_email_store().create_batch(user_id, name, sends)


async def send_batch(user_id: str, batch_id: str, *, account_id: str | None = None,
                     user: dict[str, Any] | None = None, min_delay: float = 0.0,
                     max_delay: float = 0.0) -> dict[str, Any]:
    store = get_email_store()
    batch = await store.get_batch(batch_id, user_id)
    if not batch:
        raise LookupError("email_batch_not_found")
    if account_id:
        account = await store.get_account(account_id, user_id)
    else:
        accounts = await store.list_accounts(user_id)
        account = accounts[0] if accounts else None
    if account is None:
        raise LookupError("email_account_not_configured")
    batch.status = "sending"
    crm = get_crm_store()
    sent = 0
    approval: dict[str, Any] | None = None
    for item in batch.sends:
        if item.status in {"sent", "skipped_opted_out"}:
            continue
        if crm.is_suppressed(user_id, channel="email", address=item.recipient):
            item.status = "skipped_opted_out"
            continue
        requires, reason = require_approval(user_id, [item.recipient])
        trusted = is_loopback_trusted(user or {})
        if requires and not trusted and not find_approved_approval(user_id, to_list=[item.recipient], subject=item.subject, body=item.body):
            approval = request_approval(user_id, to_list=[item.recipient], subject=item.subject, body=item.body, reason=reason, actor_id=user_id)
            batch.status = "draft"
            break
        try:
            conn = await resolve_account_connection(account)
            await asyncio.to_thread(send_smtp_message, conn, from_addr=account.email_address,
                                    to_addresses=[item.recipient], cc_addresses=[], subject=item.subject, body=item.body)
            item.status, item.sent_at, sent = "sent", _now(), sent + 1
            record_sent(crm, user_id, item.recipient)
        except Exception as exc:
            item.status, item.error = "failed", str(exc)
        if max_delay > 0:
            await asyncio.sleep(random.uniform(max(0.0, min_delay), max_delay))
    if not approval:
        batch.status = "sent" if all(s.status in {"sent", "skipped_opted_out"} for s in batch.sends) else "failed"
        if sent:
            try:
                from keprix.crm.replenish import trigger_replenish
                trigger_replenish(user_id, f"email-batch:{batch.id}", sent, actor_type="system", actor_id=user_id)
            except Exception:
                pass
        batch.sent_at = _now() if batch.status == "sent" else None
    return {"batch": batch.to_dict(), "sent": sent, "approval": approval}
