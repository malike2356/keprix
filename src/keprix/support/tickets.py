"""Support ticket intake and export."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from keprix.support.diagnostics import build_diagnostics_bundle
from keprix.support.store import get_support_store


def create_ticket(
    *,
    category: str,
    subject: str,
    description: str,
    user_id: str = "admin",
    attach_diagnostics: bool = False,
) -> dict[str, Any]:
    ticket = {
        "id": str(uuid.uuid4()),
        "category": category,
        "subject": subject,
        "description": description,
        "status": "open",
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "diagnostics_attached": attach_diagnostics,
        "diagnostics": None,
    }
    return get_support_store().save_ticket(ticket)


async def attach_diagnostics(ticket_id: str) -> dict[str, Any] | None:
    store = get_support_store()
    ticket = store.get_ticket(ticket_id)
    if ticket is None:
        return None
    bundle = await build_diagnostics_bundle()
    ticket["diagnostics"] = bundle
    ticket["diagnostics_attached"] = True
    return store.update_ticket(ticket_id, ticket)


def export_ticket(ticket_id: str) -> str | None:
    ticket = get_support_store().get_ticket(ticket_id)
    if ticket is None:
        return None
    export = {
        "ticket": {
            "id": ticket["id"],
            "category": ticket["category"],
            "subject": ticket["subject"],
            "description": ticket["description"],
            "status": ticket["status"],
            "created_at": ticket["created_at"],
        },
        "diagnostics": ticket.get("diagnostics"),
    }
    return json.dumps(export, indent=2)
