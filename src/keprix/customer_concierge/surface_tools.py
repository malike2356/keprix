"""External-customer tool catalog for web, gateway, phone, desktop, TUI (634).

Exposes the deny-by-default allowlist without granting owner privileges.
Surfaces must call gate_tool_for_current_audience / visitor_turn; this module
only publishes the catalog.
"""

from __future__ import annotations

from typing import Any

from keprix.customer_concierge.audience.tool_policy import (
    CUSTOMER_CONCIERGE_ALLOWED_TOOLS,
    CUSTOMER_CONCIERGE_BLOCKED_TOOLS,
    is_customer_concierge_tool_allowed,
)

SURFACE_KEYS = ("web", "gateway", "phone", "desktop", "tui")


def audience_tool_catalog(*, surface: str = "web") -> dict[str, Any]:
    surface_key = (surface or "web").strip().lower()
    if surface_key not in SURFACE_KEYS:
        surface_key = "web"
    allowed = sorted(CUSTOMER_CONCIERGE_ALLOWED_TOOLS)
    return {
        "surface": surface_key,
        "principal": "audience_session",
        "ownerPrivileges": False,
        "workspaceMember": False,
        "denyByDefault": True,
        "allowedTools": allowed,
        "blockedExamples": sorted(list(CUSTOMER_CONCIERGE_BLOCKED_TOOLS)[:20]),
        "execution": {
            "web": "/api/customer-concierge/public/{workspaceId}/{personaId}/session/{sessionId}/message",
            "gateway": "/api/customer-concierge/public/{workspaceId}/{personaId}/channel/session",
            "phone": "phone receptionist → audience session → same tool gate",
            "desktop": "desktop widget → public session → same tool gate",
            "tui": "keprix tui concierge preview uses audience tools only (no shell/vault)",
        },
        "note": "Prompt injection cannot expand the allowlist; enforcement is in code.",
    }


def assert_audience_tool(tool_name: str) -> dict[str, Any]:
    ok = is_customer_concierge_tool_allowed(tool_name)
    return {
        "ok": ok,
        "tool": tool_name,
        "error_code": None if ok else "audience_tool_denied",
        "ownerPrivileges": False,
    }


__all__ = ["SURFACE_KEYS", "assert_audience_tool", "audience_tool_catalog"]
