"""Safe Obsidian vault read/write and indexing."""

from __future__ import annotations

import difflib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from keprix.research_workspace.errors import ResearchWorkspaceError, UnsafeWriteError
from keprix.research_workspace.obsidian.attachments import preserve_attachment_links
from keprix.research_workspace.obsidian.backlinks import (
    backlinks_for,
    build_backlink_index,
    note_title_from_path,
)
from keprix.research_workspace.obsidian.frontmatter import dump_frontmatter, parse_frontmatter
from keprix.research_workspace.obsidian.markdown import analyze_markdown
from keprix.research_workspace.obsidian.tags import tags_from_note
from keprix.research_workspace.obsidian.vault import SyncMode, VaultConfig, should_skip_path

_KEPRIX_GENERATED_RE = re.compile(
    r"<!-- keprix:generated:start -->\n.*?\n<!-- keprix:generated:end -->",
    re.DOTALL,
)


def read_note(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    analysis = analyze_markdown(body)
    return {
        "path": str(path),
        "title": note_title_from_path(path),
        "meta": meta,
        "body": body,
        "wikilinks": analysis.wikilinks,
        "tags": tags_from_note(meta, body),
        "tasks": analysis.tasks,
        "headings": analysis.headings,
        "embeds": analysis.embeds,
    }


def index_vault(vault: VaultConfig) -> dict[str, Any]:
    root = Path(vault.local_path)
    if not root.exists():
        raise FileNotFoundError(f"Vault path not found: {root}")
    note_paths: list[Path] = []
    notes: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*.md")):
        if should_skip_path(path, root, vault):
            continue
        note_paths.append(path)
        notes.append(read_note(path))
    backlink_index = build_backlink_index(note_paths)
    for note in notes:
        note["backlinks"] = backlinks_for(note["title"], backlink_index)
    return {
        "vault_id": vault.vault_id,
        "path": str(root),
        "note_count": len(notes),
        "notes": notes,
        "backlink_index": backlink_index,
    }


def write_draft_note(
    vault: VaultConfig,
    *,
    rel_path: str,
    content: str,
    backup_dir: Path | None = None,
) -> dict[str, Any]:
    if vault.sync_mode == SyncMode.READ_ONLY:
        raise UnsafeWriteError("Vault is read-only")
    root = Path(vault.local_path)
    target = (root / rel_path).resolve()
    if root.resolve() not in target.parents and target != root.resolve():
        raise UnsafeWriteError("Note path escapes vault root")
    rel = target.relative_to(root.resolve())
    if not rel.suffix == ".md":
        target = target.with_suffix(".md")
        rel = target.relative_to(root.resolve())
    from keprix.research_workspace.obsidian.vault import is_path_allowed

    if not is_path_allowed(rel, vault):
        raise UnsafeWriteError(f"Path not allowed by vault policy: {rel}")
    backup_path: str | None = None
    if target.exists():
        original = target.read_text(encoding="utf-8")
        if "<!-- keprix:generated" not in original and vault.sync_mode != SyncMode.WRITE_APPROVED:
            raise UnsafeWriteError("Refusing to overwrite user note without approval")
        merged = preserve_attachment_links(original, content)
        if backup_dir is not None:
            backup_dir.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            backup_file = backup_dir / f"{target.stem}.{stamp}.bak.md"
            backup_file.write_text(original, encoding="utf-8")
            backup_path = str(backup_file)
            diff_file = backup_dir / f"{target.stem}.{stamp}.diff"
            diff_file.write_text(
                "\n".join(
                    difflib.unified_diff(
                        original.splitlines(),
                        merged.splitlines(),
                        fromfile=str(target),
                        tofile=str(target) + " (keprix)",
                        lineterm="",
                    )
                ),
                encoding="utf-8",
            )
        content = merged
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return {"path": str(target), "backup": backup_path, "review_status": "draft"}


def update_approved_section(path: Path, new_body: str) -> dict[str, Any]:
    original = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(original)
    if meta.get("review_status") != "approved" and meta.get("created_by") != "keprix":
        raise UnsafeWriteError("Only approved keprix notes can be updated in place")
    if "<!-- keprix:generated:start -->" not in body:
        raise UnsafeWriteError("Note has no keprix generated section")
    updated_body = _KEPRIX_GENERATED_RE.sub(
        f"<!-- keprix:generated:start -->\n{new_body.strip()}\n<!-- keprix:generated:end -->",
        body,
        count=1,
    )
    updated_body = preserve_attachment_links(body, updated_body)
    path.write_text(dump_frontmatter(meta, updated_body), encoding="utf-8")
    return {"path": str(path), "updated": True}
