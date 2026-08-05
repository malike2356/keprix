"""Sub-agent overlay state."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentNode:
    id: str
    name: str
    status: str = "idle"
    preview: str = ""
    children: list["AgentNode"] = field(default_factory=list)

    def flatten(self, depth: int = 0) -> list[str]:
        lines = [f"{'  ' * depth}{self.name} [{self.status}] {self.preview}".rstrip()]
        for child in self.children:
            lines.extend(child.flatten(depth + 1))
        return lines

