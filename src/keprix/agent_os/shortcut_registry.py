"""Keyboard shortcut normalization for Action Board pins."""

from __future__ import annotations

from typing import Any


def normalize_shortcut(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    parts = [part.strip() for part in text.replace("+", " + ").split("+") if part.strip()]
    normalized: list[str] = []
    aliases = {"control": "Ctrl", "cmd": "Meta", "command": "Meta", "option": "Alt"}
    for part in parts:
        lower = part.lower()
        normalized.append(aliases.get(lower, part[:1].upper() + part[1:]))
    return "+".join(normalized)
