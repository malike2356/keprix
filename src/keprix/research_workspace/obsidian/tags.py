"""Tag extraction and normalization for Obsidian notes."""

from __future__ import annotations

from typing import Any

from keprix.research_workspace.obsidian.markdown import extract_inline_tags


def normalize_tag(tag: str) -> str:
    cleaned = tag.strip().lstrip("#")
    return cleaned.replace(" ", "-").lower()


def tags_from_note(meta: dict[str, Any], body: str) -> list[str]:
    tags: list[str] = []
    front = meta.get("tags")
    if isinstance(front, list):
        tags.extend(str(item) for item in front)
    elif isinstance(front, str) and front:
        tags.append(front)
    tags.extend(extract_inline_tags(body))
    seen: set[str] = set()
    ordered: list[str] = []
    for tag in tags:
        normalized = normalize_tag(tag)
        if normalized and normalized not in seen:
            seen.add(normalized)
            ordered.append(normalized)
    return ordered
