"""Todo panel model for the TUI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TodoItem:
    id: str
    text: str
    done: bool = False


class TodoPanelState:
    def __init__(self, items: list[TodoItem] | None = None) -> None:
        self.items = list(items or [])

    def add(self, item_id: str, text: str) -> None:
        self.items.append(TodoItem(id=item_id, text=text))

    def toggle(self, item_id: str) -> bool:
        for item in self.items:
            if item.id == item_id:
                item.done = not item.done
                return item.done
        raise KeyError(item_id)

    def remove(self, item_id: str) -> None:
        self.items = [item for item in self.items if item.id != item_id]

    def render(self) -> str:
        if not self.items:
            return "No todos"
        return "\n".join(f"[{'x' if item.done else ' '}] {item.text}" for item in self.items)

