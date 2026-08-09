"""Command Center action models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ActionKind = Literal[
    "slash",
    "session",
    "model",
    "skill",
    "plugin",
    "file",
    "vault",
    "runtime",
    "help",
    "ui",
]

ActionEffect = Literal["insert", "execute", "open", "switch", "toggle", "copy"]


@dataclass(frozen=True)
class CommandCenterAction:
    id: str
    title: str
    description: str
    kind: ActionKind
    effect: ActionEffect = "execute"
    value: str = ""
    category: str = ""
    keywords: tuple[str, ...] = ()
    disabled: bool = False
    metadata: dict[str, str] = field(default_factory=dict)

    def search_text(self) -> str:
        return " ".join(
            part
            for part in (
                self.id,
                self.title,
                self.description,
                self.kind,
                self.category,
                " ".join(self.keywords),
            )
            if part
        ).lower()


def action_id(kind: str, value: str) -> str:
    safe_value = value.strip().lower().replace(" ", "-")
    return f"{kind}:{safe_value}"


__all__ = ["ActionEffect", "ActionKind", "CommandCenterAction", "action_id"]
