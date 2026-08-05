from pathlib import Path

from keprix.keprix_cli.vault_commands import _migrate_workspace, _vault_doctor


def test_vault_doctor_reports_health(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("hello", encoding="utf-8")

    result = _vault_doctor(str(tmp_path))

    assert result["file_count"] == 1
    assert result["status"] in {"healthy", "warning"}


def test_migrate_workspace_copies_markdown(tmp_path: Path) -> None:
    source = tmp_path / "workspace"
    vault = tmp_path / "vault"
    (source / "documents").mkdir(parents=True)
    (source / "documents" / "brief.md").write_text("brief", encoding="utf-8")

    result = _migrate_workspace(str(source), str(vault))

    assert result["files_migrated"] == 1
    assert (vault / "wiki" / "from-workspace" / "documents" / "brief.md").read_text(encoding="utf-8") == "brief"
