"""Audit writer for generated tools."""

from __future__ import annotations

from typing import Any

from keprix.agent.keprix.schemas import GeneratedToolRecord
from keprix.agent.keprix.store import GeneratedToolStore, get_generated_tool_store


class MutationAuditor:
    def __init__(self, store: GeneratedToolStore | None = None) -> None:
        self._store = store or get_generated_tool_store()

    def record_synthesis(self, **kwargs: Any) -> GeneratedToolRecord:
        return self._store.create(**kwargs)

    def mark_approved(self, record_id: str, *, approver_id: str, channel: str) -> GeneratedToolRecord | None:
        from datetime import datetime, timezone

        return self._store.update(
            record_id,
            status="approved",
            approver_id=approver_id,
            approver_channel=channel,
            approved_at=datetime.now(timezone.utc).isoformat(),
        )

    def mark_rejected(self, record_id: str, *, approver_id: str, channel: str, reason: str | None) -> GeneratedToolRecord | None:
        from datetime import datetime, timezone

        return self._store.update(
            record_id,
            status="rejected",
            approver_id=approver_id,
            approver_channel=channel,
            rejection_reason=reason,
            rejected_at=datetime.now(timezone.utc).isoformat(),
        )

    def mark_installed(self, record_id: str) -> GeneratedToolRecord | None:
        from datetime import datetime, timezone

        return self._store.update(
            record_id,
            status="installed",
            installed_at=datetime.now(timezone.utc).isoformat(),
        )
