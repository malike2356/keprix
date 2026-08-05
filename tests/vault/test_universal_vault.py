"""Prompt 259 universal vault provider tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.tools.vault_tools import vault_read, vault_search, vault_write
from keprix.vault.config import VaultConfig, save_vault_config
from keprix.vault.local_folder import LocalFolderVault


@pytest.fixture
def vault_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / ".keprix"
    root.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(root))
    return root


@pytest.mark.asyncio
async def test_local_folder_vault_roundtrip_preserves_frontmatter(tmp_path: Path) -> None:
    vault = LocalFolderVault(tmp_path)
    await vault.write_file("wiki/page.md", "---\ntitle: Old\n---\n\nOld body")
    await vault.write_file("wiki/page.md", "New body")

    content = await vault.read_file("wiki/page.md")

    assert "title: Old" in content
    assert "New body" in content
    files = await vault.list_files("wiki")
    assert files[0].path == "wiki/page.md"


@pytest.mark.asyncio
async def test_wikilinks_backlinks_search_and_graph(tmp_path: Path) -> None:
    vault = LocalFolderVault(tmp_path)
    await vault.write_file("wiki/page-a.md", "Links to [[page-b]] and project notes")
    await vault.write_file("wiki/page-b.md", "Target page")

    search = await vault.search("page-b")
    backlinks = await vault.get_backlinks("wiki/page-b.md")
    graph = await vault.get_graph()

    assert any(item.path == "wiki/page-a.md" for item in search)
    assert backlinks == ["wiki/page-a.md"]
    assert {"source": "wiki/page-a.md", "target": "wiki/page-b.md"} in graph["edges"]


def test_vault_routes_config_read_write_search(vault_home: Path, tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("Hello [[other]]", encoding="utf-8")
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    config = client.put("/api/vault/config", json={"provider": "local_folder", "root_path": str(tmp_path), "watch": True})
    assert config.status_code == 200

    listed = client.get("/api/vault/files")
    assert listed.status_code == 200
    assert listed.json()["files"][0]["path"] == "note.md"

    written = client.put("/api/vault/files/wiki/new.md", json={"content": "New [[note]]"})
    assert written.status_code == 200
    read = client.get("/api/vault/files/wiki/new.md")
    assert read.json()["content"] == "New [[note]]"
    search = client.get("/api/vault/search?query=note")
    assert search.status_code == 200
    graph = client.get("/api/vault/graph")
    assert graph.status_code == 200
    assert graph.json()["nodes"]


def test_vault_tools_use_configured_provider(vault_home: Path, tmp_path: Path) -> None:
    save_vault_config(VaultConfig(root_path=str(tmp_path)))
    result = vault_write("daily.md", "Daily note")
    assert result["ok"] is True
    assert vault_read("daily.md") == "Daily note"
    results = vault_search("daily")
    assert results["results"][0]["path"] == "daily.md"
