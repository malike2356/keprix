"""Slash command history model."""

from dataclasses import dataclass, field


@dataclass
class CommandHistory:
    max_items: int = 500
    items: list[str] = field(default_factory=list)

    def push(self, command: str) -> None:
        command = command.strip()
        if not command.startswith("/"):
            return
        if self.items and self.items[-1] == command:
            return
        self.items.append(command)
        self.items[:] = self.items[-self.max_items :]

    def recent(self, limit: int = 20) -> list[str]:
        return self.items[-limit:]


__all__ = ["CommandHistory"]
