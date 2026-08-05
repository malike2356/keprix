"""Session-scoped registry for in-flight web/TUI conversation turns.

Maps ``session_id`` to the live ``AIAgent`` (when the agent tool loop is
running) plus stream control state. Entries are created when
``POST /api/conversations/{id}/messages`` begins streaming and removed when
the NDJSON generator finishes or disconnects.

Steer and interrupt endpoints read this registry; they do not spawn agents.
"""

from __future__ import annotations

import asyncio
import threading
from dataclasses import dataclass, field
from typing import Any


class NotBusyError(Exception):
    """Raised when steer/interrupt is requested but no active turn exists."""


BUSY_INPUT_MODES = ("interrupt", "queue", "steer")


def normalize_busy_input_mode(raw: str | None) -> str:
    mode = (raw or "interrupt").strip().lower()
    if mode in BUSY_INPUT_MODES:
        return mode
    return "interrupt"


def get_busy_input_mode() -> str:
    from keprix.keprix_cli.config import cfg_get, load_config_readonly

    config = load_config_readonly()
    return normalize_busy_input_mode(cfg_get(config, "display", "busy_input_mode", default="interrupt"))


@dataclass
class ActiveTurn:
    session_id: str
    agent: Any | None = None
    partial_chars: int = 0
    queue_depth: int = 0
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)


class TurnRegistry:
    """Thread-safe map of session_id to active turn control state."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._turns: dict[str, ActiveTurn] = {}

    def register(self, session_id: str) -> ActiveTurn:
        with self._lock:
            turn = ActiveTurn(session_id=session_id)
            self._turns[session_id] = turn
            return turn

    def unregister(self, session_id: str) -> None:
        with self._lock:
            self._turns.pop(session_id, None)

    def get(self, session_id: str) -> ActiveTurn | None:
        with self._lock:
            return self._turns.get(session_id)

    def attach_agent(self, session_id: str, agent: Any) -> None:
        with self._lock:
            turn = self._turns.get(session_id)
            if turn is not None:
                turn.agent = agent

    def detach_agent(self, session_id: str) -> None:
        with self._lock:
            turn = self._turns.get(session_id)
            if turn is not None:
                turn.agent = None

    def set_partial_chars(self, session_id: str, count: int) -> None:
        with self._lock:
            turn = self._turns.get(session_id)
            if turn is not None:
                turn.partial_chars = max(0, int(count))

    def is_busy(self, session_id: str) -> bool:
        return self.get(session_id) is not None

    def steer(self, session_id: str, text: str) -> int:
        cleaned = (text or "").strip()
        if not cleaned:
            raise ValueError("empty steer text")
        with self._lock:
            turn = self._turns.get(session_id)
            if turn is None or turn.agent is None:
                raise NotBusyError(session_id)
            agent = turn.agent
        steer_fn = getattr(agent, "steer", None)
        if not callable(steer_fn):
            raise NotBusyError(session_id)
        if not steer_fn(cleaned):
            raise ValueError("empty steer text")
        return len(cleaned)

    def interrupt(self, session_id: str) -> bool:
        with self._lock:
            turn = self._turns.get(session_id)
            if turn is None:
                return False
            agent = turn.agent
            cancel_event = turn.cancel_event
        if agent is not None:
            interrupt_fn = getattr(agent, "interrupt", None)
            if callable(interrupt_fn):
                interrupt_fn()
        cancel_event.set()
        return True

    def snapshot(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            turn = self._turns.get(session_id)
            if turn is None:
                return {
                    "busy": False,
                    "mode": get_busy_input_mode(),
                    "queue_depth": 0,
                    "partial_chars": 0,
                }
            return {
                "busy": True,
                "mode": get_busy_input_mode(),
                "queue_depth": turn.queue_depth,
                "partial_chars": turn.partial_chars,
            }


turn_registry = TurnRegistry()
