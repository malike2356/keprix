"""Research note templates for Obsidian export."""

from __future__ import annotations

from typing import Any

from keprix.research_workspace.obsidian.frontmatter import dump_frontmatter
from keprix.research_workspace.obsidian.markdown import wikilink

NOTE_TYPES = (
    "literature",
    "source",
    "claim",
    "dataset",
    "meeting",
    "field",
    "research_summary",
)

PROVENANCE_KEYS = (
    "keprix_project_id",
    "keprix_source_id",
    "keprix_trace_id",
    "created_by",
    "review_status",
)


def render_research_note(
    note_type: str,
    *,
    title: str,
    body: str,
    project_id: str,
    trace_id: str,
    source_id: str | None = None,
    backlinks: list[str] | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> str:
    if note_type not in NOTE_TYPES:
        raise ValueError(f"Unsupported note type: {note_type}")
    meta: dict[str, Any] = {
        "title": title,
        "type": note_type,
        "keprix_project_id": project_id,
        "keprix_source_id": source_id or "",
        "keprix_trace_id": trace_id,
        "created_by": "keprix",
        "review_status": "draft",
        "tags": [note_type, "keprix", "draft"],
    }
    if extra_meta:
        meta.update(extra_meta)
    link_lines = [wikilink(name) for name in (backlinks or [])]
    header = f"# {title}\n\n"
    links_block = ("\n".join(link_lines) + "\n\n") if link_lines else ""
    keprix_block = (
        "<!-- keprix:generated:start -->\n"
        f"{body.strip()}\n"
        "<!-- keprix:generated:end -->\n"
    )
    return dump_frontmatter(meta, header + links_block + keprix_block)


def note_filename(note_type: str, object_id: str) -> str:
    return f"{note_type}-{object_id}.md"
