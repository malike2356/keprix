"""Persistent Ponytail debt ledger."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from keprix_constants import get_keprix_home

MARKER_RE = re.compile(r"(?:#|//)\s*ponytail:\s*(?P<text>.*)")


@dataclass
class DebtItem:
    id: int
    path: str
    line: int
    text: str
    status: str = "open"

    def to_dict(self) -> dict:
        return self.__dict__.copy()


def _ledger_path() -> Path:
    path = get_keprix_home() / "coding" / "ponytail-debt.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def list_debt() -> list[DebtItem]:
    path = _ledger_path()
    if not path.exists():
        return []
    return [DebtItem(**item) for item in json.loads(path.read_text(encoding="utf-8"))]


def save_debt(items: list[DebtItem]) -> list[DebtItem]:
    _ledger_path().write_text(json.dumps([item.to_dict() for item in items], indent=2), encoding="utf-8")
    return items


def add_debt(text: str, *, path: str = "manual", line: int = 0) -> DebtItem:
    items = list_debt()
    item = DebtItem(id=(max((item.id for item in items), default=0) + 1), path=path, line=line, text=text)
    save_debt([*items, item])
    return item


def resolve_debt(item_id: int) -> DebtItem | None:
    items = list_debt()
    found = None
    for item in items:
        if item.id == item_id:
            item.status = "resolved"
            found = item
    save_debt(items)
    return found


def harvest_debt(root: str | Path) -> list[DebtItem]:
    base = Path(root)
    harvested: list[DebtItem] = []
    for path in sorted(base.rglob("*")):
        if path.is_dir() or any(part in {".git", ".venv", "node_modules", "__pycache__"} for part in path.parts):
            continue
        if path.suffix not in {".py", ".ts", ".tsx", ".js", ".jsx"}:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
            match = MARKER_RE.search(line)
            if match:
                harvested.append(add_debt(match.group("text").strip(), path=str(path), line=number))
    return harvested
