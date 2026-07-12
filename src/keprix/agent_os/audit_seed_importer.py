"""Import Personal OS audit seeds into the workflow audit store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from keprix.agent_os.audit_store import AuditStore, AuditTask, WorkflowAuditResult


def import_audit_seed(path: str | Path, *, user_id: str | None = None) -> WorkflowAuditResult:
    source = Path(path)
    data = json.loads(source.read_text(encoding="utf-8"))
    store = AuditStore()
    audit = store.create(mode="manual", user_id=user_id)
    audit.status = "draft"
    audit.tasks = [
        AuditTask(
            id=str(item.get("id") or item.get("description") or "seed-task"),
            domain=str(item.get("domain") or "general"),
            description=str(item.get("description") or ""),
            frequency=str(item.get("frequency") or "weekly"),
            desired_output=str(item.get("desired_output") or ""),
            tools_hint=list(item.get("tools_hint") or []),
            propose_skill=bool(item.get("propose_skill", True)),
            propose_automation=bool(item.get("propose_automation", False)),
        )
        for item in data.get("tasks") or []
    ]
    store.save(audit)
    return audit
