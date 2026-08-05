"""Prompt 272 vault validator tests."""

from __future__ import annotations

from pathlib import Path

from keprix.vault.vault_validator import validate_vault


def test_validate_empty_dir_fails_with_clear_errors(tmp_path: Path) -> None:
    result = validate_vault(tmp_path)

    assert result["ok"] is False
    assert "Vault manifest missing" in result["errors"][0]
    assert "Missing KEPRIX.md" in result["errors"]
