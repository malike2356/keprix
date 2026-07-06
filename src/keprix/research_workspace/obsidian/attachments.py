"""Attachment embed preservation for Obsidian notes."""

from __future__ import annotations

import re

from keprix.research_workspace.obsidian.markdown import EMBED_RE, extract_embeds

_ATTACHMENT_LINE_RE = re.compile(r"^!\[\[[^\]]+\]\]\s*$", re.MULTILINE)


def extract_attachment_embeds(body: str) -> list[str]:
    return extract_embeds(body)


def attachment_block(body: str) -> str:
    lines = [line for line in body.splitlines() if _ATTACHMENT_LINE_RE.match(line)]
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def preserve_attachment_links(original_body: str, new_body: str) -> str:
    embeds = extract_attachment_embeds(original_body)
    if not embeds:
        return new_body
    missing = [embed for embed in embeds if embed not in new_body]
    if not missing:
        return new_body
    block = "\n".join(f"![[{name}]]" for name in missing)
    return new_body.rstrip() + "\n\n## Attachments\n\n" + block + "\n"
