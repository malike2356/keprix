"""Runtime control flags applied by ScoutListener commands."""

from __future__ import annotations

_egress_force_blocked = False
_blocked_sessions: set[str] = set()
_quarantined_tools: set[str] = set()


def egress_force_blocked() -> bool:
    return _egress_force_blocked


def set_egress_force_blocked(blocked: bool) -> None:
    global _egress_force_blocked
    _egress_force_blocked = blocked


def block_session(session_id: str) -> None:
    _blocked_sessions.add(session_id)


def unblock_session(session_id: str) -> None:
    _blocked_sessions.discard(session_id)


def is_session_blocked(session_id: str | None) -> bool:
    if not session_id:
        return False
    return session_id in _blocked_sessions


def quarantine_tool(tool_name: str) -> None:
    _quarantined_tools.add(tool_name)


def lift_quarantine(tool_name: str) -> None:
    _quarantined_tools.discard(tool_name)


def is_tool_quarantined(tool_name: str) -> bool:
    return tool_name in _quarantined_tools


def reset_scout_control() -> None:
    global _egress_force_blocked
    _egress_force_blocked = False
    _blocked_sessions.clear()
    _quarantined_tools.clear()


def snapshot() -> dict[str, object]:
    return {
        "egress_force_blocked": _egress_force_blocked,
        "blocked_sessions": sorted(_blocked_sessions),
        "quarantined_tools": sorted(_quarantined_tools),
    }
