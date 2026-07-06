"""Prompt 42 adapter tests."""

from __future__ import annotations

import json

from keprix.backend.migration.adapters.hermes import HermesAdapter
from keprix.backend.migration.adapters.markdown import MarkdownAdapter


def test_hermes_adapter_reads_memory_and_skills(tmp_path):
    export_dir = tmp_path / "export"
    export_dir.mkdir()
    (export_dir / "memory.json").write_text(
        json.dumps([{"key": "Language", "value": "English"}]),
        encoding="utf-8",
    )
    (export_dir / "skills.json").write_text(
        json.dumps([{"name": "Summarize", "body": "Summarize text.", "category": "writing"}]),
        encoding="utf-8",
    )
    conv_dir = export_dir / "conversations"
    conv_dir.mkdir()
    (conv_dir / "abc.json").write_text(
        json.dumps({"messages": [{"role": "user", "content": "Hello"}]}),
        encoding="utf-8",
    )

    manifest = HermesAdapter().convert(export_dir)
    assert manifest.schema_version == "agent-migration.v1"
    assert manifest.summary.counts_by_kind["memory"] == 1
    assert manifest.summary.counts_by_kind["skill"] == 1
    assert manifest.summary.counts_by_kind["archive_document"] == 1
    assert manifest.validate_integrity() == []


def test_markdown_adapter_archive_and_memory_candidate(tmp_path):
    notes_dir = tmp_path / "notes"
    notes_dir.mkdir()
    (notes_dir / "long-note.md").write_text("# Long note\n\n" + ("x" * 400), encoding="utf-8")
    (notes_dir / "pref.md").write_text("I prefer dark mode", encoding="utf-8")

    manifest = MarkdownAdapter().convert(notes_dir)
    kinds = manifest.summary.counts_by_kind
    assert kinds["archive_document"] == 2
    assert kinds["memory"] == 1
    memory_items = [item for item in manifest.items if item.kind == "memory"]
    assert memory_items[0].memory_confidence == 0.5
