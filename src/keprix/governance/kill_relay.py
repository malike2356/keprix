"""Governance kill directive relay state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class KillState:
    stop_agent: bool = False
    lock_workspace: bool = False
    disable_tools: bool = False
    active_directives: list[dict[str, Any]] = field(default_factory=list)
    updated_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "stop_agent": self.stop_agent,
            "lock_workspace": self.lock_workspace,
            "disable_tools": self.disable_tools,
            "active_directives": list(self.active_directives),
            "updated_at": self.updated_at,
        }


_state = KillState()
_stop_event = asyncio.Event()


def get_kill_state() -> KillState:
    return _state


def apply_kill_directive(directive_type: str, payload: dict[str, Any] | None = None) -> None:
    payload = payload or {}
    now = datetime.now(timezone.utc).isoformat()
    record = {"type": directive_type, "payload": payload, "received_at": now}
    _state.active_directives.append(record)
    _state.updated_at = now
    if directive_type == "stop_agent":
        _state.stop_agent = True
        _stop_event.set()
    elif directive_type == "lock_workspace":
        _state.lock_workspace = True
    elif directive_type == "disable_tools":
        _state.disable_tools = True


def clear_kill_state() -> None:
    global _state, _stop_event
    _state = KillState()
    _stop_event = asyncio.Event()


def resume_agent() -> None:
    """Clear a suspend/stop directive without wiping other kill state."""
    _state.stop_agent = False
    _stop_event.clear()
    _state.updated_at = datetime.now(timezone.utc).isoformat()


def agent_stop_requested() -> bool:
    return _state.stop_agent


def workspace_locked() -> bool:
    return _state.lock_workspace


def tools_disabled() -> bool:
    return _state.disable_tools or _state.stop_agent


async def wait_for_agent_stop(timeout: float = 5.0) -> bool:
    if not _state.stop_agent:
        return False
    try:
        await asyncio.wait_for(_stop_event.wait(), timeout=timeout)
        return True
    except TimeoutError:
        return False
