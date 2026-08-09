"""Workspace / tenant / user scope mapping (Prompt 629).

``workspace_id`` is the tenant scope key for every store query and job.
``tenant_id`` is an alias of ``workspace_id`` in contract language.
``user_id`` is a workspace member/operator id and must never be treated as an
external visitor principal (audience sessions land in Prompt 630).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConciergeScope:
    workspace_id: str
    persona_id: str = "default"
    user_id: str | None = None

    @property
    def tenant_id(self) -> str:
        return self.workspace_id

    @property
    def concierge_binding(self) -> str:
        return f"{self.workspace_id}:{self.persona_id}"


def resolve_scope(
    *,
    workspace_id: str | None = None,
    tenant_id: str | None = None,
    user_id: str | None = None,
    persona_id: str | None = None,
    x_workspace_id: str | None = None,
) -> ConciergeScope:
    ws = (workspace_id or tenant_id or x_workspace_id or user_id or "default").strip() or "default"
    return ConciergeScope(
        workspace_id=ws,
        persona_id=(persona_id or "default").strip() or "default",
        user_id=(user_id.strip() if user_id else None),
    )


def assert_workspace_match(expected: str, actual: str | None, *, field: str = "workspace_id") -> None:
    if not actual or str(actual).strip() != str(expected).strip():
        raise PermissionError(f"workspace_mismatch:{field}")


def filter_rows_for_workspace(rows: list[dict[str, Any]], workspace_id: str) -> list[dict[str, Any]]:
    """Enforce tenant scope on in-memory/JSON rows (workspaceId or workspace_id)."""
    out: list[dict[str, Any]] = []
    for row in rows:
        wid = row.get("workspaceId") or row.get("workspace_id")
        if wid is None and isinstance(row.get("object"), dict):
            wid = row["object"].get("workspaceId") or row["object"].get("workspace_id")
        if str(wid or "") == workspace_id:
            out.append(row)
    return out
