"""Message dispatch runtime for multi-agent coordination (Prompt 58)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from keprix.backend.multiagent.message import AgentMessage, MessageType

MessageHandler = Callable[[AgentMessage], None | Awaitable[None]]

_message_log: list[AgentMessage] = []
_handlers: dict[str, list[MessageHandler]] = {}
_run_events: dict[str, list[dict[str, Any]]] = {}


async def send_message(message: AgentMessage) -> AgentMessage:
    """Dispatch a structured message to a sibling agent."""
    _message_log.append(message)
    _record_run_event(message.run_id, "message_sent", message.to_dict())
    handlers = _handlers.get(message.recipient, [])
    for handler in handlers:
        result = handler(message)
        if hasattr(result, "__await__"):
            await result
    return message


def register_handler(agent_id: str, handler: MessageHandler) -> None:
    _handlers.setdefault(agent_id, []).append(handler)


def get_messages(
    *,
    workspace_id: str | None = None,
    run_id: str | None = None,
    sender: str | None = None,
    recipient: str | None = None,
    message_type: MessageType | None = None,
) -> list[AgentMessage]:
    results = list(_message_log)
    if workspace_id is not None:
        results = [m for m in results if m.workspace_id == workspace_id]
    if run_id is not None:
        results = [m for m in results if m.run_id == run_id]
    if sender is not None:
        results = [m for m in results if m.sender == sender]
    if recipient is not None:
        results = [m for m in results if m.recipient == recipient]
    if message_type is not None:
        results = [m for m in results if m.message_type == message_type]
    return results


def get_run_events(run_id: str) -> list[dict[str, Any]]:
    return list(_run_events.get(run_id, []))


def _record_run_event(run_id: str, event_type: str, payload: dict[str, Any]) -> None:
    _run_events.setdefault(run_id, []).append({"type": event_type, "payload": payload})


def clear_messages() -> None:
    _message_log.clear()
    _handlers.clear()
    _run_events.clear()
