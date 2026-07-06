"""Prompt 42 manifest tests."""

from __future__ import annotations

from keprix.backend.migration.manifest import (
    AgentMigrationManifest,
    MigrationItem,
    MigrationSource,
    MigrationSummary,
    build_manifest,
)


def test_validate_integrity_detects_count_mismatch():
    manifest = AgentMigrationManifest(
        schema_version="agent-migration.v1",
        generated_at=build_manifest(
            source=MigrationSource(name="test", kind="generic"),
            items=[MigrationItem(kind="memory", id="m-0", title="A", content="fact")],
        ).generated_at,
        source=MigrationSource(name="test", kind="generic"),
        summary=MigrationSummary(item_count=2, counts_by_kind={"memory": 2}, warning_count=0),
        items=[MigrationItem(kind="memory", id="m-0", title="A", content="fact")],
    )
    errors = manifest.validate_integrity()
    assert any("item_count" in error for error in errors)
    assert any("counts_by_kind" in error for error in errors)


def test_build_manifest_counts_by_kind():
    items = [
        MigrationItem(kind="memory", id="m-0", title="A", content="one"),
        MigrationItem(kind="skill", id="s-0", title="B", content="body"),
    ]
    manifest = build_manifest(source=MigrationSource(name="hermes-agent", kind="hermes"), items=items)
    assert manifest.summary.item_count == 2
    assert manifest.summary.counts_by_kind == {"memory": 1, "skill": 1}
    assert manifest.validate_integrity() == []
