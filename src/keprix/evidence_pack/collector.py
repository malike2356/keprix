"""Collect clinical events and linked documents for evidence packs."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Any

from keprix.export.store import get_export_store
from keprix.governance.audit_events import AUDIT_EVENT_TYPES
from keprix.governance.audit_store import get_audit_event_store


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def collect_audit_events(
    workspace_id: str,
    date_from: datetime,
    date_to: datetime,
    event_types: list[str] | None = None,
    domain_pack: str | None = None,
) -> list[dict[str, Any]]:
    allowed = set(AUDIT_EVENT_TYPES)
    types = [item for item in (event_types or list(allowed)) if item in allowed]
    return get_audit_event_store().list_events(
        workspace_id,
        date_from=date_from,
        date_to=date_to,
        event_types=types,
        domain_pack=domain_pack,
    )


async def collect_linked_documents(
    workspace_id: str,
    events: list[dict[str, Any]],
) -> list[tuple[str, bytes]]:
    del workspace_id
    exports = get_export_store()
    documents: list[tuple[str, bytes]] = []
    seen: set[str] = set()
    for event in events:
        detail = event.get("detail") or {}
        file_id = detail.get("export_file_id") or detail.get("file_id")
        if not file_id or file_id in seen:
            continue
        path = exports.resolve_path(str(file_id))
        if path is None or not path.exists():
            continue
        seen.add(str(file_id))
        name = path.name
        if not name.lower().endswith(".pdf"):
            continue
        documents.append((name, path.read_bytes()))
    return documents


async def export_audit_csv(
    workspace_id: str,
    date_from: datetime,
    date_to: datetime,
) -> str:
    events = await collect_audit_events(workspace_id, date_from, date_to)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        ["event_id", "event_type", "timestamp", "actor_type", "summary", "severity", "domain_pack"]
    )
    for event in events:
        writer.writerow(
            [
                event.get("event_id"),
                event.get("event_type"),
                event.get("timestamp"),
                event.get("actor_type"),
                event.get("summary"),
                event.get("severity"),
                event.get("domain_pack"),
            ]
        )
    return buffer.getvalue()
