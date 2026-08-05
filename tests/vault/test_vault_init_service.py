"""Prompt 272 vault init service tests."""

from __future__ import annotations

import json
from pathlib import Path

from keprix.vault.vault_init_service import init_vault, render_vault_template
from keprix.vault.vault_validator import validate_vault


def test_vault_init_copies_obsidian_starter_tree(tmp_path: Path) -> None:
    vault = tmp_path / "vault"

    result = init_vault(pack="obsidian-starter", path=str(vault))

    assert (vault / "KEPRIX.md").is_file()
    assert (vault / "00-inbox").is_dir()
    assert (vault / "01-projects").is_dir()
    assert (vault / "templates" / "daily-note.md").is_file()
    manifest = json.loads((vault / ".keprix" / "vault-manifest.json").read_text(encoding="utf-8"))
    assert manifest["pack"] == "obsidian-vault-starter"
    assert manifest["folders"]["inbox"] == "00-inbox"
    assert result["manifest_path"].endswith(".keprix/vault-manifest.json")


def test_vault_init_is_idempotent_without_overwriting_keprix_md(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    init_vault(pack="obsidian-starter", path=str(vault))
    (vault / "KEPRIX.md").write_text("custom", encoding="utf-8")

    init_vault(pack="obsidian-starter", path=str(vault))

    assert (vault / "KEPRIX.md").read_text(encoding="utf-8") == "custom"


def test_render_vault_template_replaces_date_placeholder(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    init_vault(pack="obsidian-starter", path=str(vault))

    result = render_vault_template(vault_path=str(vault), template="daily-note", values={"date": "2026-07-09"})

    assert "{{date}}" not in result["content"]
    assert "2026-07-09" in result["content"]


def test_initialized_vault_validates(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    init_vault(pack="obsidian-starter", path=str(vault))

    result = validate_vault(vault)

    assert result["ok"] is True
    assert result["errors"] == []
