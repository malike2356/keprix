"""Localization audit logging."""

from __future__ import annotations

import uuid
from typing import Any

from keprix.backend.localization.schemas import LocalizationAuditRecord
from keprix.backend.localization.store import get_localization_store


class LocalizationAuditService:
    def __init__(self) -> None:
        self._store = get_localization_store()

    async def write(self, record: LocalizationAuditRecord) -> dict[str, Any]:
        payload = record.to_dict()
        payload["id"] = str(uuid.uuid4())
        return await self._store.append_audit(record.workspace_id, payload)

    async def list_records(
        self,
        workspace_id: str,
        *,
        limit: int = 50,
        human_review_required: bool | None = None,
    ) -> list[dict[str, Any]]:
        return await self._store.list_audit(
            workspace_id,
            limit=limit,
            human_review_required=human_review_required,
        )

    async def get_record(self, workspace_id: str, audit_id: str) -> dict[str, Any] | None:
        return await self._store.get_audit_record(workspace_id, audit_id)


_audit_service: LocalizationAuditService | None = None


def get_audit_service() -> LocalizationAuditService:
    global _audit_service
    if _audit_service is None:
        _audit_service = LocalizationAuditService()
    return _audit_service


def reset_audit_service() -> None:
    global _audit_service
    _audit_service = None
