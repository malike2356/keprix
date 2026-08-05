"""Web UI / TUI prompt bridge for clarify and exec approval.

Registers gateway-style notify hooks and clarify callbacks on the agent worker
thread so HTTP clients can unblock blocked turns via respond endpoints.
"""

from __future__ import annotations

import logging
import os
import threading
import uuid
from typing import Any, Callable

logger = logging.getLogger(__name__)

EmitFn = Callable[[str, dict[str, Any]], None]

_lock = threading.Lock()
_approval_ids: dict[str, str] = {}


def get_tui_clarify_timeout_sec() -> int:
    raw = os.environ.get("KEPRIX_TUI_CLARIFY_TIMEOUT_SEC", "300")
    try:
        return max(1, int(raw))
    except (TypeError, ValueError):
        return 300


def _emit(emit: EmitFn | None, event: str, payload: dict[str, Any]) -> None:
    if emit is None:
        return
    try:
        emit(event, payload)
    except Exception as exc:
        logger.warning("web UI prompt emit failed for %s: %s", event, exc)


def build_clarify_callback(session_id: str, emit: EmitFn | None) -> Callable[[str, list[str] | None], str]:
    from tools import clarify_gateway as clarify_mod

    def _callback(question: str, choices: list[str] | None) -> str:
        clarify_id = uuid.uuid4().hex[:10]
        clarify_mod.register(
            clarify_id=clarify_id,
            session_key=session_id,
            question=question,
            choices=list(choices) if choices else None,
        )
        payload_choices = list(choices) if choices else []
        _emit(
            emit,
            "clarify",
            {
                "clarify_id": clarify_id,
                "question": question,
                "choices": payload_choices,
            },
        )
        timeout = float(min(clarify_mod.get_clarify_timeout(), get_tui_clarify_timeout_sec()))
        response = clarify_mod.wait_for_response(clarify_id, timeout=timeout)
        if response is None or response == "":
            return f"[user did not respond within {int(timeout / 60)}m]"
        return str(response)

    return _callback


def build_approval_notify(session_id: str, emit: EmitFn | None) -> Callable[[dict[str, Any]], None]:
    def _notify(approval_data: dict[str, Any]) -> None:
        approval_id = uuid.uuid4().hex[:10]
        with _lock:
            _approval_ids[approval_id] = session_id
        _emit(
            emit,
            "approval",
            {
                "approval_id": approval_id,
                "command": str(approval_data.get("command") or ""),
                "description": str(approval_data.get("description") or ""),
                "allow_permanent": bool(approval_data.get("allow_permanent", True)),
            },
        )

    return _notify


def respond_clarify(clarify_id: str, answer: str) -> bool:
    from tools import clarify_gateway as clarify_mod

    return clarify_mod.resolve_gateway_clarify(clarify_id, answer)


def respond_approval(session_id: str, approval_id: str, decision: str) -> bool:
    from tools.approval import resolve_gateway_approval

    with _lock:
        owner = _approval_ids.pop(approval_id, None)
    if owner is not None and owner != session_id:
        return False
    choice = normalize_approval_decision(decision)
    count = resolve_gateway_approval(session_id, choice)
    return count > 0


def normalize_approval_decision(decision: str) -> str:
    raw = (decision or "").strip().lower()
    if raw in {"once", "y", "yes", "approve"}:
        return "once"
    if raw in {"always", "a", "all"}:
        return "always"
    if raw in {"session", "s"}:
        return "session"
    return "deny"


def activate_web_ui_prompt_session(session_id: str, emit: EmitFn | None) -> tuple[Callable[[], None], Any]:
    """Configure approval/clarify hooks for one agent worker thread."""
    import os

    from tools.approval import register_gateway_notify, reset_current_session_key, set_current_session_key, unregister_gateway_notify

    token = set_current_session_key(session_id)
    os.environ["KEPRIX_GATEWAY_SESSION"] = "1"
    register_gateway_notify(session_id, build_approval_notify(session_id, emit))

    def _cleanup() -> None:
        unregister_gateway_notify(session_id)
        reset_current_session_key(token)
        os.environ.pop("KEPRIX_GATEWAY_SESSION", None)
        from tools import clarify_gateway as clarify_mod

        clarify_mod.clear_session(session_id)

    return _cleanup, build_clarify_callback(session_id, emit)
