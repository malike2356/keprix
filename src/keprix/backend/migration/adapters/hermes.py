"""Hermes agent export adapter (Prompt 42)."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.backend.migration.adapters._helpers import flatten_conversation
from keprix.backend.migration.manifest import (
    MigrationItem,
    MigrationSource,
    MigrationWarning,
    build_manifest,
)


class HermesAdapter:
    def convert(self, export_dir: Path):
        items: list[MigrationItem] = []
        warnings: list[MigrationWarning] = []

        memory_path = export_dir / "memory.json"
        if memory_path.exists():
            memories = json.loads(memory_path.read_text(encoding="utf-8"))
            for index, mem in enumerate(memories):
                items.append(
                    MigrationItem(
                        kind="memory",
                        id=f"memory-{index}",
                        title=mem.get("key", f"Memory {index}"),
                        content=mem.get("value", ""),
                        memory_confidence=0.9,
                    )
                )
        else:
            warnings.append(MigrationWarning(item_index=None, message="memory.json not found", severity="warn"))

        skills_path = export_dir / "skills.json"
        if skills_path.exists():
            skills = json.loads(skills_path.read_text(encoding="utf-8"))
            for index, skill in enumerate(skills):
                items.append(
                    MigrationItem(
                        kind="skill",
                        id=f"skill-{index}",
                        title=skill.get("name", f"Skill {index}"),
                        content=skill.get("body", ""),
                        skill_category=skill.get("category"),
                    )
                )

        conv_dir = export_dir / "conversations"
        if conv_dir.exists():
            for conv_file in sorted(conv_dir.glob("*.json")):
                try:
                    conv = json.loads(conv_file.read_text(encoding="utf-8"))
                    items.append(
                        MigrationItem(
                            kind="archive_document",
                            id=f"conv-{conv_file.stem}",
                            title=f"Conversation {conv_file.stem}",
                            content=flatten_conversation(conv),
                            source_path=str(conv_file),
                        )
                    )
                except (json.JSONDecodeError, KeyError) as exc:
                    warnings.append(
                        MigrationWarning(
                            item_index=None,
                            message=f"Could not parse {conv_file.name}: {exc}",
                            severity="warn",
                        )
                    )

        return build_manifest(
            source=MigrationSource(name="hermes-agent", kind="hermes"),
            items=items,
            warnings=warnings,
        )
