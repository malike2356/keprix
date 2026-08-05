"""Prompt 278 hot cache service tests."""

from __future__ import annotations

from pathlib import Path

from keprix.workspace.hot_cache_service import HotCacheService
from keprix.workspace.template_presets import create_workspace


def test_disabled_workspace_does_not_write_hot_cache(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()

    result = HotCacheService().refresh("demo", workspace_path=str(workspace), recent_text="alpha beta")

    assert result["written"] is False
    assert not (workspace / "wiki" / "hot.md").exists()


def test_enabled_refresh_writes_capped_hot_cache(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    service = HotCacheService()
    service.set_config("demo", True, str(workspace))
    long_text = " ".join(f"word{i}" for i in range(900))

    result = service.refresh("demo", workspace_path=str(workspace), source_session_id="sess-1", summary=long_text)

    assert result["written"] is True
    content = (workspace / "wiki" / "hot.md").read_text(encoding="utf-8")
    assert "sess-1" in content
    assert len(content.split()) <= 600


def test_executive_assistant_preset_enables_hot_cache(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))

    create_workspace("ea", "executive_assistant")
    root = tmp_path / ".keprix" / "workspaces" / "ea"

    assert HotCacheService().get_config("ea").enabled is True
    assert (root / "wiki" / "hot.md").is_file()
    assert (root / "wiki" / "index.md").is_file()
    assert (root / "wiki" / "log.md").is_file()
