"""Markdown parsing helpers for Obsidian notes."""

from __future__ import annotations

import re
from dataclasses import dataclass

WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]")
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
TAG_RE = re.compile(r"(?<!\w)#([a-zA-Z][\w/-]*)")
TASK_RE = re.compile(r"^\s*-\s+\[([ xX])\]\s+(.+)$", re.MULTILINE)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
EMBED_RE = re.compile(r"!\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]")


@dataclass
class MarkdownNote:
    body: str
    wikilinks: list[str]
    markdown_links: list[tuple[str, str]]
    tags: list[str]
    tasks: list[tuple[bool, str]]
    headings: list[tuple[int, str]]
    embeds: list[str]


def analyze_markdown(body: str) -> MarkdownNote:
    return MarkdownNote(
        body=body,
        wikilinks=extract_wikilinks(body),
        markdown_links=extract_markdown_links(body),
        tags=extract_inline_tags(body),
        tasks=extract_tasks(body),
        headings=extract_headings(body),
        embeds=extract_embeds(body),
    )


def extract_wikilinks(text: str) -> list[str]:
    return [match.group(1).strip() for match in WIKILINK_RE.finditer(text)]


def extract_markdown_links(text: str) -> list[tuple[str, str]]:
    return [(match.group(1), match.group(2)) for match in MD_LINK_RE.finditer(text)]


def extract_inline_tags(text: str) -> list[str]:
    return [match.group(1) for match in TAG_RE.finditer(text)]


def extract_tasks(text: str) -> list[tuple[bool, str]]:
    tasks: list[tuple[bool, str]] = []
    for match in TASK_RE.finditer(text):
        done = match.group(1).lower() == "x"
        tasks.append((done, match.group(2).strip()))
    return tasks


def extract_headings(text: str) -> list[tuple[int, str]]:
    return [(len(match.group(1)), match.group(2).strip()) for match in HEADING_RE.finditer(text)]


def extract_embeds(text: str) -> list[str]:
    return [match.group(1).strip() for match in EMBED_RE.finditer(text)]


def wikilink(target: str, alias: str | None = None) -> str:
    if alias and alias != target:
        return f"[[{target}|{alias}]]"
    return f"[[{target}]]"
