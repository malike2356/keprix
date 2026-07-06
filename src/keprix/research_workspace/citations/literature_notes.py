"""Literature note generation from citations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from keprix.research_workspace.citations.models import CitationRecord
from keprix.research_workspace.obsidian.templates import note_filename, render_research_note


def literature_note_body(record: CitationRecord, sections: dict[str, str] | None = None) -> str:
    sections = sections or {}
    authors = ", ".join(record.authors) if record.authors else "Unknown"
    lines = [
        "## Citation metadata",
        f"- Citation key: `{record.citation_key}`",
        f"- Authors: {authors}",
        f"- Year: {record.year or 'n.d.'}",
        f"- Publication: {record.publication or 'n/a'}",
        f"- DOI: {record.doi or 'n/a'}",
        f"- URL: {record.url or 'n/a'}",
        "",
        "## Summary",
        sections.get("summary") or (record.abstract or "Add summary."),
        "",
        "## Key claims",
        sections.get("key_claims") or "- ",
        "",
        "## Methods",
        sections.get("methods") or "- ",
        "",
        "## Findings",
        sections.get("findings") or "- ",
        "",
        "## Limitations",
        sections.get("limitations") or "- ",
        "",
        "## Relevance to project",
        sections.get("relevance") or "Describe why this source matters.",
    ]
    if record.tags:
        lines.extend(["", "## Tags", ", ".join(f"`{tag}`" for tag in record.tags)])
    return "\n".join(lines)


def generate_literature_note(
    record: CitationRecord,
    *,
    project_id: str,
    trace_id: str,
    sections: dict[str, str] | None = None,
    obsidian_note_path: str | None = None,
) -> dict[str, Any]:
    body = literature_note_body(record, sections=sections)
    backlinks = ["index"]
    content = render_research_note(
        "literature",
        title=record.title,
        body=body,
        project_id=project_id,
        trace_id=trace_id,
        source_id=record.item_key,
        backlinks=backlinks,
        extra_meta={
            "zotero_item_key": record.item_key,
            "citation_key": record.citation_key,
            "zotero_source": record.source,
        },
    )
    suggested_path = obsidian_note_path or note_filename("literature", record.citation_key)
    record.obsidian_note_path = suggested_path
    return {
        "content": content,
        "path": suggested_path,
        "citation_key": record.citation_key,
        "record": record.to_dict(),
    }


def write_literature_note_to_vault(
    *,
    vault_root: Path,
    rel_path: str,
    content: str,
) -> str:
    target = vault_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Literature note already exists: {target}")
    target.write_text(content, encoding="utf-8")
    return str(target)
