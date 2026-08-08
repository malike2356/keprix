"""Simple CRM role checks (view/edit/approve/export/send)."""

from __future__ import annotations

from typing import Any

ROLE_CAPS = {
    "viewer": frozenset({"view"}),
    "editor": frozenset({"view", "edit"}),
    "approver": frozenset({"view", "edit", "approve"}),
    "sender": frozenset({"view", "edit", "approve", "send"}),
    "admin": frozenset({"view", "edit", "approve", "send", "export"}),
    "owner": frozenset({"view", "edit", "approve", "send", "export"}),
}


def role_from_user(user: dict[str, Any]) -> str:
    role = str(user.get("role") or user.get("crm_role") or "").strip().lower()
    if role in ROLE_CAPS:
        return role
    # Default session users can edit and approve Soft Wall items in CE.
    return "admin"


def require_cap(user: dict[str, Any], capability: str) -> None:
    role = role_from_user(user)
    caps = ROLE_CAPS.get(role, frozenset())
    if capability not in caps:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=403,
            detail={"error_code": "crm_forbidden", "capability": capability, "role": role},
        )
