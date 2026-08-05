"""Prompt 258 structured workspace memory tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.auth.dependencies import get_current_user
from keprix.memory.episodic.store import InMemoryEpisodicStore
from keprix.workspace.cli_commands import _dispatch
from keprix.workspace.index_generator import WorkspaceIndexer
from keprix.workspace.keprix_md_generator import render_keprix_md
from keprix.workspace.memory_index_bridge import MemoryIndexBridge
from keprix.workspace.template_presets import create_workspace, get_template, list_templates, workspace_root


@pytest.fixture
def workspace_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / ".keprix"
    root.mkdir()
    monkeypatch.setenv("KEPRIX_HOME", str(root))
    return root


def test_index_generator_updates_parent_index(workspace_home: Path) -> None:
    root = workspace_home / "workspaces" / "demo"
    raw = root / "raw"
    raw.mkdir(parents=True)
    source = raw / "market-report-draft.md"
    source.write_text("Portsmouth market notes", encoding="utf-8")

    indexer = WorkspaceIndexer(root)
    content = indexer.update_index("raw")

    assert "| [market-report-draft.md](market-report-draft.md) | Market Report Draft |" in content
    assert "Draft" in content
    source.unlink()
    updated = indexer.on_file_change(raw / "market-report-draft.md", "deleted")
    assert "No files yet" in updated


def test_template_create_writes_indexes_and_keprix_md(workspace_home: Path) -> None:
    workspace = create_workspace("knowledge hub", "knowledge_pipeline")
    root = Path(str(workspace["path"]))

    assert (root / "raw" / "index.md").is_file()
    assert (root / "wiki" / "index.md").is_file()
    guide = (root / "KEPRIX.md").read_text(encoding="utf-8")
    assert "Read the nearest `index.md`" in guide
    assert "`/raw/`" in guide
    assert (root / "CLAUDE.md").read_text(encoding="utf-8") == guide


def test_template_presets_include_expected_folders() -> None:
    templates = {template.id: template for template in list_templates()}
    assert {"raw", "wiki", "outputs"}.issubset(set(templates["knowledge_pipeline"].folders))
    assert "context" in get_template("executive_assistant").folders


def test_keprix_md_mentions_hot_cache_when_present(workspace_home: Path) -> None:
    root = workspace_home / "workspaces" / "exec"
    (root / "wiki").mkdir(parents=True)
    (root / "wiki" / "hot.md").write_text("priority context", encoding="utf-8")
    content = render_keprix_md(root, get_template("executive_assistant"))
    assert "wiki/hot.md" in content
    assert "context/" in content


@pytest.mark.asyncio
async def test_memory_index_bridge_returns_file_paths(workspace_home: Path) -> None:
    file_path = workspace_home / "workspaces" / "demo" / "wiki" / "pricing-models.md"
    file_path.parent.mkdir(parents=True)
    file_path.write_text("Pricing model comparison for agent apps", encoding="utf-8")
    bridge = MemoryIndexBridge(store=InMemoryEpisodicStore(), user_id="u1")

    memory_id = await bridge.link_file(file_path, workspace_id="demo")
    paths = await bridge.recall_paths("pricing model", limit=5)

    assert memory_id
    assert str(file_path) in paths


def test_workspace_template_routes(workspace_home: Path) -> None:
    app = create_app()
    app.dependency_overrides[get_current_user] = lambda: {"id": "u1", "role": "user"}
    client = TestClient(app)

    templates = client.get("/api/workspaces/templates")
    assert templates.status_code == 200
    assert any(item["id"] == "knowledge_pipeline" for item in templates.json()["templates"])

    created = client.post("/api/workspaces", json={"name": "client hub", "template_id": "client_delivery"})
    assert created.status_code == 200
    workspace_id = created.json()["workspace"]["id"]
    reindexed = client.post(f"/api/workspaces/{workspace_id}/reindex", json={"folder": "deliverables"})
    assert reindexed.status_code == 200
    assert "index.md" in reindexed.json()["updated"][0]


def test_workspace_cli_init_and_index(workspace_home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    import argparse

    init_args = argparse.Namespace(workspace_command="init", name="cli hub", template="developer")
    assert _dispatch(init_args) == 0
    assert (workspace_root("cli hub") / "KEPRIX.md").is_file()

    index_args = argparse.Namespace(workspace_command="index", name="cli hub", folder="specs")
    assert _dispatch(index_args) == 0
    assert "# /specs -- Index" in capsys.readouterr().out
