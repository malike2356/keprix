"""Session switcher state for the TUI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionPreview:
    id: str
    title: str
    preview: str = ""
    last_active: str = ""


class SessionSwitcherState:
    def __init__(self, sessions: list[SessionPreview] | None = None) -> None:
        self.sessions = list(sessions or [])
        self.index = 0

    def cycle(self, step: int = 1) -> SessionPreview | None:
        if not self.sessions:
            return None
        self.index = (self.index + step) % len(self.sessions)
        return self.sessions[self.index]

    def close(self, session_id: str) -> None:
        self.sessions = [session for session in self.sessions if session.id != session_id]
        self.index = min(self.index, max(0, len(self.sessions) - 1))

