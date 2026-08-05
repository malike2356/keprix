from __future__ import annotations

from pathlib import Path

import pytest

from keprix.sync.syncthing.config import load_config, save_api_key, save_config
from keprix.sync.syncthing.policy import paths_overlap, validate_separation
from keprix.sync.syncthing.service import get_status, update_settings


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / ".keprix"
    home.mkdir()
    (home / "vault").mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(home))
    monkeypatch.delenv("SYNCTHING_API_KEY", raising=False)
    monkeypatch.delenv("KEPRIX_SYNCTHING_API_KEY", raising=False)


def test_paths_overlap_and_forbidden(tmp_path: Path) -> None:
    vault = tmp_path / ".keprix" / "vault"
    clone = tmp_path / ".keprix" / "data" / "github-agent-sync" / "ws"
    clone.mkdir(parents=True)
    assert paths_overlap(str(vault), str(vault))
    warnings = validate_separation(vault_path=str(clone), agent_sync_clone=None)
    assert warnings
    warnings2 = validate_separation(vault_path=str(vault), agent_sync_clone=str(clone))
    assert warnings2 == []
    nested = clone / "notes"
    nested.mkdir()
    assert paths_overlap(str(clone), str(nested))


def test_one_writer_disables_on_agent_sync_overlap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    bad = tmp_path / ".keprix" / "data" / "github-agent-sync" / "ws"
    bad.mkdir(parents=True)
    save_api_key("test-key")
    result = update_settings(
        {
            "enabled": True,
            "vaultPath": str(bad),
            "writerRole": "home",
            "baseUrl": "http://127.0.0.1:8384",
        }
    )
    assert result.get("enabled") is False
    assert result.get("ok") is False
    assert "overlap" in (result.get("error") or "").lower() or any("overlap" in w for w in (result.get("warnings") or []))


def test_config_save_and_status(tmp_path: Path) -> None:
    vault = tmp_path / ".keprix" / "vault"
    save_config(
        {
            "enabled": False,
            "vault_path": str(vault),
            "syncthing_path": "/var/syncthing/vault",
            "writer_role": "home",
            "base_url": "http://syncthing:8384",
        }
    )
    save_api_key("secret-key")
    status = get_status()
    assert status["configured"] is True
    assert status["has_api_key"] is True
    assert status["writer_role"] == "home"
    assert status["folder_type"] == "receiveonly"
    assert status["syncthing_path"] == "/var/syncthing/vault"
    assert status["one_writer"]["keprix_vault_read_only"] is True
    cfg = load_config()
    assert cfg.folder_id == "keprix-obsidian-vault"
