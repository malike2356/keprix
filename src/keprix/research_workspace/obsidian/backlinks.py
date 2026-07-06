"""Backlink index for Obsidian vault notes."""

from __future__ import annotations

from pathlib import Path

from keprix.research_workspace.obsidian.frontmatter import parse_frontmatter
from keprix.research_workspace.obsidian.markdown import extract_wikilinks


def note_title_from_path(path: Path) -> str:
    return path.stem


def build_backlink_index(note_paths: list[Path]) -> dict[str, list[str]]:
    index: dict[str, set[str]] = {}
    for path in note_paths:
        source = note_title_from_path(path)
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        _, body = parse_frontmatter(text)
        for target in extract_wikilinks(body):
            index.setdefault(target, set()).add(source)
    return {key: sorted(values) for key, values in index.items()}


def backlinks_for(note_name: str, index: dict[str, list[str]]) -> list[str]:
    return list(index.get(note_name, []))


def forward_links_for(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    _, body = parse_frontmatter(text)
    return extract_wikilinks(body)
