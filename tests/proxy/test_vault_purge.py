"""Legacy vault purge tests."""

from __future__ import annotations

import json

from keprix.proxy.paths import local_vault_path
from keprix.proxy.vault_purge import purge_legacy_vault


def test_vault_purge_requires_confirmation(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().write_text(json.dumps({"secrets": {"openai-api-key": "sk"}}), encoding="utf-8")

    result = purge_legacy_vault(confirm=False)

    assert result["requires_confirmation"] is True
    assert local_vault_path().is_file()


def test_vault_purge_backs_up_and_deletes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path))
    local_vault_path().write_text(json.dumps({"secrets": {"openai-api-key": "sk"}}), encoding="utf-8")

    result = purge_legacy_vault(confirm=True)

    assert result["purged"] is True
    assert not local_vault_path().exists()
    assert result["backup_path"]
