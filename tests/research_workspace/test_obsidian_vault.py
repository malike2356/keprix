"""Obsidian vault adapter tests."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from keprix.data_architecture.data_plane import WorkspaceDataPlane
from keprix.research_workspace.errors import VaultPathError
from keprix.research_workspace.obsidian.sync import index_vault, read_note, update_approved_section, write_draft_note
from keprix.research_workspace.obsidian.templates import render_research_note
from keprix.research_workspace.obsidian.vault import VaultConfig, VaultRegistry, validate_vault_path


@pytest.fixture
def workspace_root(tmp_path):
    plane = WorkspaceDataPlane(workspace_id=f"ws-{uuid.uuid4().hex[:6]}")
    plane.root = tmp_path / "workspace"
    plane.db_path = plane.root / "data_plane.sqlite"
    plane.initialize()
    return plane.root


def test_register_vault_inside_workspace(workspace_root):
    vault_path = workspace_root / "vaults" / "research"
    registry = VaultRegistry(workspace_root)
    vault = registry.register(name="Research", local_path=str(vault_path))
    assert vault.vault_id.startswith("vault-")
    assert Path(vault.local_path).exists()
    assert len(registry.list_vaults()) == 1


def test_external_path_requires_approval(workspace_root, tmp_path):
    external = tmp_path / "external-vault"
    external.mkdir()
    with pytest.raises(VaultPathError):
        validate_vault_path(external, workspace_root=workspace_root, allow_external=False)
    resolved = validate_vault_path(external, workspace_root=workspace_root, allow_external=True)
    assert resolved == external.resolve()


def test_index_vault_without_obsidian_running(workspace_root):
    vault_dir = workspace_root / "vaults" / "notes"
    vault_dir.mkdir(parents=True)
    (vault_dir / "alpha.md").write_text("---\ntitle: Alpha\ntags: [note]\n---\n\n# Alpha\n\nSee [[beta]].\n", encoding="utf-8")
    (vault_dir / "beta.md").write_text("---\ntitle: Beta\n---\n\n# Beta\n", encoding="utf-8")
    vault = VaultConfig(
        vault_id="vault-test",
        name="Notes",
        local_path=str(vault_dir),
    )
    indexed = index_vault(vault)
    assert indexed["note_count"] == 2
    alpha = next(note for note in indexed["notes"] if note["title"] == "alpha")
    assert "beta" in alpha["wikilinks"]
    assert "alpha" in indexed["backlink_index"]["beta"]


def test_write_draft_literature_note_with_backlinks(workspace_root):
    vault_dir = workspace_root / "vaults" / "drafts"
    vault_dir.mkdir(parents=True)
    vault = VaultConfig(vault_id="vault-draft", name="Drafts", local_path=str(vault_dir))
    content = render_research_note(
        "literature",
        title="Groundwater yield study",
        body="Summary of borehole measurements.",
        project_id="rp-test",
        trace_id="trace-abc",
        source_id="src-1",
        backlinks=["index"],
    )
    result = write_draft_note(
        vault,
        rel_path="literature-src-1.md",
        content=content,
        backup_dir=workspace_root / "backups",
    )
    saved = read_note(Path(result["path"]))
    assert saved["meta"]["keprix_project_id"] == "rp-test"
    assert saved["meta"]["review_status"] == "draft"
    assert "[[index]]" in saved["body"]
    assert "keprix:generated" in saved["body"]


def test_refuse_overwrite_user_note(workspace_root):
    vault_dir = workspace_root / "vaults" / "safe"
    vault_dir.mkdir(parents=True)
    user_note = vault_dir / "my-note.md"
    user_note.write_text("# My manual note\n\nUser content.\n", encoding="utf-8")
    vault = VaultConfig(vault_id="vault-safe", name="Safe", local_path=str(vault_dir))
    from keprix.research_workspace.errors import UnsafeWriteError

    with pytest.raises(UnsafeWriteError):
        write_draft_note(vault, rel_path="my-note.md", content="# overwrite\n")


def test_update_approved_generated_section(workspace_root):
    vault_dir = workspace_root / "vaults" / "approved"
    vault_dir.mkdir(parents=True)
    note_path = vault_dir / "approved-note.md"
    note_path.write_text(
        render_research_note(
            "claim",
            title="Approved claim",
            body="Original text.",
            project_id="rp-1",
            trace_id="trace-1",
            extra_meta={"review_status": "approved"},
        ),
        encoding="utf-8",
    )
    result = update_approved_section(note_path, "Updated approved text.")
    assert result["updated"] is True
    saved = read_note(note_path)
    assert "Updated approved text." in saved["body"]
