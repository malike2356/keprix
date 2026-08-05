"""Input history model."""

from __future__ import annotations

from pathlib import Path


class InputHistory:
    """Previous submitted prompts; navigate with arrow keys."""

    def __init__(self, max_items: int = 10_000, path: Path | None = None) -> None:
        self._items: list[str] = []
        self._max_items = max_items
        self._path = path
        self._index = -1
        self._draft = ""
        if path is not None:
            self.load(path)

    def push(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        if self._items and self._items[-1] == text:
            return
        self._items.append(text)
        if len(self._items) > self._max_items:
            self._items = self._items[-self._max_items :]
        self._index = -1
        self._draft = ""
        if self._path is not None:
            self.save(self._path)

    def begin_navigate(self, current: str) -> None:
        if self._index == -1:
            self._draft = current

    def previous(self) -> str | None:
        if not self._items:
            return None
        if self._index == -1:
            self._index = len(self._items) - 1
        elif self._index > 0:
            self._index -= 1
        return self._items[self._index]

    def next(self) -> str | None:
        if self._index < 0:
            return None
        if self._index < len(self._items) - 1:
            self._index += 1
            return self._items[self._index]
        self._index = -1
        return self._draft

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(item.replace("\n", "\\n") for item in self._items), encoding="utf-8")

    def load(self, path: Path) -> None:
        if not path.exists():
            return
        items = [line.rstrip("\n").replace("\\n", "\n") for line in path.read_text(encoding="utf-8").splitlines()]
        self._items = [item for item in items if item][-self._max_items :]

    def snapshot(self) -> list[str]:
        return list(self._items)


__all__ = ["InputHistory"]
