"""Markdown notes folder adapter (Prompt 42)."""

from __future__ import annotations

import re
from pathlib import Path

from keprix.backend.migration.manifest import MigrationItem, MigrationSource, build_manifest


class MarkdownAdapter:
    MEMORY_CANDIDATE_MAX_CHARS = 300
    MEMORY_CANDIDATE_PATTERNS = [
        r"^(I|My|The user|User) (prefer|use|like|hate|always|never|am|is|was)",
        r"^(Name|Email|Company|Role|Location|Language):",
    ]

    def convert(self, notes_dir: Path):
        items: list[MigrationItem] = []
        md_files = sorted(notes_dir.rglob("*.md"))
        for index, path in enumerate(md_files):
            try:
                text = path.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                continue
            if not text:
                continue
            relative = str(path.relative_to(notes_dir))
            items.append(
                MigrationItem(
                    kind="archive_document",
                    id=f"md-{index}",
                    title=path.stem,
                    content=text,
                    source_path=relative,
                )
            )
            if len(text) <= self.MEMORY_CANDIDATE_MAX_CHARS:
                for pattern in self.MEMORY_CANDIDATE_PATTERNS:
                    if re.search(pattern, text, re.IGNORECASE):
                        items.append(
                            MigrationItem(
                                kind="memory",
                                id=f"md-mem-{index}",
                                title=f"Memory candidate from {path.stem}",
                                content=text,
                                memory_confidence=0.5,
                                source_path=relative,
                            )
                        )
                        break
        return build_manifest(source=MigrationSource(name="markdown-notes", kind="markdown"), items=items)
