"""Prompt injector sections tracked by section id (not substring)."""

from __future__ import annotations

import threading
from typing import Any, Callable

_LOCK = threading.RLock()
# section_id -> {plugin_id, content | factory}
_SECTIONS: dict[str, dict[str, Any]] = {}


def register_prompt_section(
    section_id: str,
    content: str | Callable[[], str],
    *,
    plugin_id: str,
) -> None:
    """Register a prompt section. *section_id* must be stable and unique."""
    if not section_id or not isinstance(section_id, str):
        raise ValueError("section_id must be a non-empty string")
    with _LOCK:
        existing = _SECTIONS.get(section_id)
        if existing and existing.get("plugin_id") != plugin_id:
            raise ValueError(
                f"prompt section {section_id!r} already owned by "
                f"{existing.get('plugin_id')!r}"
            )
        _SECTIONS[section_id] = {
            "plugin_id": plugin_id,
            "content": content,
        }


def clear_prompt_section(section_id: str) -> bool:
    with _LOCK:
        return _SECTIONS.pop(section_id, None) is not None


def get_prompt_section(section_id: str) -> str | None:
    with _LOCK:
        entry = _SECTIONS.get(section_id)
        if entry is None:
            return None
        content = entry.get("content")
        if callable(content):
            return str(content())
        return str(content) if content is not None else None


def list_prompt_sections(*, plugin_id: str | None = None) -> list[str]:
    with _LOCK:
        if plugin_id is None:
            return sorted(_SECTIONS.keys())
        return sorted(
            sid
            for sid, meta in _SECTIONS.items()
            if meta.get("plugin_id") == plugin_id
        )


def render_prompt_sections(*, plugin_id: str | None = None) -> str:
    """Join active sections for injection (ordered by section_id)."""
    parts: list[str] = []
    for sid in list_prompt_sections(plugin_id=plugin_id):
        text = get_prompt_section(sid)
        if text and text.strip():
            parts.append(f"<!-- keprix-prompt-section:{sid} -->\n{text.strip()}")
    return "\n\n".join(parts)


def reset_prompt_sections_for_tests() -> None:
    with _LOCK:
        _SECTIONS.clear()
