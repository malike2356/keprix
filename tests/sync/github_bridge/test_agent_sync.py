from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.sync.github_bridge.config import GithubBridgeScope, load_config, save_config, save_token
from keprix.sync.github_bridge.policy import content_looks_secret, should_commit_file
from keprix.sync.github_bridge.service import get_status, search_shared_knowledge, write_durable_note
from keprix.sync.github_bridge.index_store import build_chunk, save_index, search_index


@pytest.fixture(autouse=True)
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_HOME", str(tmp_path / ".keprix"))
    monkeypatch.delenv("AGENT_SYNC_GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)


def test_policy_rejects_secrets_and_ephemeral() -> None:
    ok, reason = should_commit_file(
        rel_path="memory/agents/keprix/note.md",
        content="ghp_abcdefghijklmnopqrstuvwxyz0123456789",
        allowed_write_folders=["memory/agents"],
    )
    assert ok is False
    assert reason and "secret" in reason
    assert content_looks_secret("token = 'supersecretvalue'")


def test_config_save_and_status(tmp_path: Path) -> None:
    scope = GithubBridgeScope(scope_kind="workspace", scope_id="default", workspace_id="default")
    save_config(
        {
            "enabled": True,
            "owner": "malike2356",
            "repo": "agent-sync",
            "product": "keprix",
        },
        scope,
    )
    save_token("test-token", scope)
    status = get_status(scope)
    assert status["enabled"] is True
    assert status["has_token"] is True
    assert status["repo"] == "malike2356/agent-sync"
    assert status["product"] == "keprix"
    cfg = load_config(scope)
    assert cfg.owner == "malike2356"


def test_index_search_and_note_policy(tmp_path: Path) -> None:
    scope = GithubBridgeScope(scope_kind="workspace", workspace_id="default")
    save_config({"enabled": True, "owner": "o", "repo": "r", "product": "keprix"}, scope)
    chunks = [
        build_chunk(path="memory/agents/keprix/hello.md", content="Fowler and Keprix share durable notes", product="keprix", agent="keprix")
    ]
    save_index(chunks, scope)
    hits = search_shared_knowledge("Fowler durable", scope=scope)
    assert hits
    assert "Fowler" in hits[0]["snippet"] or hits[0]["score"] > 0

    # Clone missing: note write creates file under configured local path after we set one
    repo = tmp_path / "repo"
    (repo / "memory" / "agents" / "keprix").mkdir(parents=True)
    save_config({"local_path": str(repo), "enabled": True}, scope)
    result = write_durable_note(
        relative_path="memory/agents/keprix/from-test.md",
        content="# Hello from Keprix\n\nDurable note for Fowler sync.\n",
        push=False,
        scope=scope,
    )
    assert result["ok"] is True
    assert (repo / "memory" / "agents" / "keprix" / "from-test.md").is_file()
