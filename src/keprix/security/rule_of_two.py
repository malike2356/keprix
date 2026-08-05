"""Minimal session-level Rule of Two scorer."""

from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class RuleOfTwoState:
    private_data: bool = False
    untrusted_content: bool = False
    external_side_effect: bool = False
    human_approval_required: bool = False
    last_reason: str | None = None
    tools: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "private_data": self.private_data,
            "untrusted_content": self.untrusted_content,
            "external_side_effect": self.external_side_effect,
            "human_approval_required": self.human_approval_required,
            "last_reason": self.last_reason,
            "tools": list(self.tools),
        }

    @property
    def hot(self) -> bool:
        return sum(1 for flag in (self.private_data, self.untrusted_content, self.external_side_effect) if flag) >= 2


_lock = threading.Lock()
_sessions: dict[str, RuleOfTwoState] = {}


def _session_key(session_id: str | None) -> str:
    return (session_id or os.getenv("KEPRIX_SESSION_ID") or "default").strip() or "default"


def get_state(session_id: str | None) -> RuleOfTwoState:
    key = _session_key(session_id)
    with _lock:
        state = _sessions.get(key)
        if state is None:
            state = RuleOfTwoState()
            _sessions[key] = state
        return state


def reset_state(session_id: str | None = None) -> None:
    key = _session_key(session_id)
    with _lock:
        _sessions.pop(key, None)


def record_leg(
    session_id: str | None,
    *,
    private_data: bool | None = None,
    untrusted_content: bool | None = None,
    external_side_effect: bool | None = None,
    tool_name: str | None = None,
    last_reason: str | None = None,
) -> RuleOfTwoState:
    state = get_state(session_id)
    if private_data is not None:
        state.private_data = state.private_data or bool(private_data)
    if untrusted_content is not None:
        state.untrusted_content = state.untrusted_content or bool(untrusted_content)
    if external_side_effect is not None:
        state.external_side_effect = state.external_side_effect or bool(external_side_effect)
    if tool_name:
        state.tools.append(tool_name)
    if last_reason:
        state.last_reason = last_reason
    state.human_approval_required = state.hot
    return state


def should_require_human_approval(session_id: str | None, *, tool_name: str | None = None) -> bool:
    state = get_state(session_id)
    if tool_name:
        state.tools.append(tool_name)
    return state.hot

