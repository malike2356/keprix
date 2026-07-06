"""Setup audit trail (in-memory, no secrets)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class SetupAuditRecord:
    id: str
    workspace_id: str
    user_id: str
    service_id: str
    action: str
    status: str
    vault_item_id: str | None = None
    validation_summary: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class SetupAuditStore:
    def __init__(self) -> None:
        self._rows: list[SetupAuditRecord] = []

    def append(
        self,
        *,
        workspace_id: str,
        user_id: str,
        service_id: str,
        action: str,
        status: str,
        vault_item_id: str | None = None,
        validation_summary: str | None = None,
    ) -> SetupAuditRecord:
        record = SetupAuditRecord(
            id=str(uuid.uuid4()),
            workspace_id=workspace_id,
            user_id=user_id,
            service_id=service_id,
            action=action,
            status=status,
            vault_item_id=vault_item_id,
            validation_summary=validation_summary,
        )
        self._rows.append(record)
        return record

    def list_rows(self, *, limit: int = 100) -> list[dict[str, Any]]:
        rows = self._rows[-limit:]
        return [
            {
                "id": row.id,
                "workspace_id": row.workspace_id,
                "user_id": row.user_id,
                "service_id": row.service_id,
                "action": row.action,
                "status": row.status,
                "vault_item_id": row.vault_item_id,
                "validation_summary": row.validation_summary,
                "created_at": row.created_at.isoformat(),
            }
            for row in reversed(rows)
        ]


_store: SetupAuditStore | None = None


def get_setup_audit() -> SetupAuditStore:
    global _store
    if _store is None:
        _store = SetupAuditStore()
    return _store


def reset_setup_audit() -> None:
    global _store
    _store = SetupAuditStore()
