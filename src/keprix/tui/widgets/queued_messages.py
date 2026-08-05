"""Queued message state."""

from __future__ import annotations


class QueuedMessagesState:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def enqueue(self, text: str) -> None:
        cleaned = text.strip()
        if cleaned:
            self.messages.append(cleaned)

    def flush(self) -> list[str]:
        messages = self.messages
        self.messages = []
        return messages

    def render(self) -> str:
        count = len(self.messages)
        return f"{count} queued" if count else "No queued messages"

