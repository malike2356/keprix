"""Tests for scoped self-coding harness (Prompt 153)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.mutation.config import get_mutation_settings
from keprix.mutation.self_coding_harness import SelfCodingRequest, run_scoped_mutation
from keprix.mutation.store import MutationStore


@pytest.fixture
def mutation_store(tmp_path, monkeypatch):
    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    monkeypatch.setattr("keprix.mutation.store._store", store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: store)
    return store, tmp_path


def _mock_git(monkeypatch, repo_root: Path):
    state = {"branch": "main", "branches": {"main"}}

    def fake_current(repo):
        return state["branch"]

    def fake_create(repo, branch_name):
        state["branch"] = branch_name
        state["branches"].add(branch_name)
        from keprix.mutation.self_coding_git import GitCommandResult

        return GitCommandResult(ok=True)

    def fake_delete(repo, branch_name, checkout=None):
        state["branches"].discard(branch_name)
        state["branch"] = checkout or "main"
        from keprix.mutation.self_coding_git import GitCommandResult

        return GitCommandResult(ok=True)

    monkeypatch.setattr("keprix.mutation.self_coding_harness.current_branch", fake_current)
    monkeypatch.setattr("keprix.mutation.self_coding_harness.create_branch", fake_create)
    monkeypatch.setattr("keprix.mutation.self_coding_harness.delete_branch", fake_delete)
    monkeypatch.setattr("keprix.mutation.self_coding_git.current_branch", fake_current)


@pytest.mark.asyncio
async def test_scoped_mutation_creates_branch(mutation_store, monkeypatch, tmp_path):
    store, db_tmp = mutation_store
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setenv("KEPRIX_MUTATION_SELF_CODING", "true")
    monkeypatch.setenv("KEPRIX_MUTATION_REPO_ROOT", str(repo_root))
    get_mutation_settings.cache_clear()
    _mock_git(monkeypatch, repo_root)

    def good_runner(repo, request, allowed):
        rel = "src/keprix/tools/timestamp_tool.py"
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# tool\n", encoding="utf-8")
        diff = f"--- /dev/null\n+++ b/{rel}\n@@ -0,0 +1 @@\n+# tool\n"
        return diff, [rel], None

    monkeypatch.setattr("keprix.mutation.self_coding_harness.run_tests", lambda _repo: type("R", (), {"ok": True, "output": "ok"})())

    request = SelfCodingRequest(
        task="create a tool that returns the current timestamp",
        target_dir="src/keprix/tools/",
        workspace_id="default",
        requested_by="operator",
    )
    result = await run_scoped_mutation(request, store, repo_root, coding_runner=good_runner)
    assert result.success is True
    assert result.scope_valid is True
    assert result.mutation_id is not None
    assert result.branch_name.startswith("mutation/")


@pytest.mark.asyncio
async def test_scope_violation_aborts_and_deletes_branch(mutation_store, monkeypatch, tmp_path):
    store, _db = mutation_store
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setenv("KEPRIX_MUTATION_SELF_CODING", "true")
    get_mutation_settings.cache_clear()
    deleted = {"called": False}
    _mock_git(monkeypatch, repo_root)

    def fake_delete(repo, branch_name, checkout=None):
        deleted["called"] = True
        from keprix.mutation.self_coding_git import GitCommandResult

        return GitCommandResult(ok=True)

    monkeypatch.setattr("keprix.mutation.self_coding_harness.delete_branch", fake_delete)

    def bad_runner(repo, request, allowed):
        diff = """--- a/src/keprix/vault/secret.py
+++ b/src/keprix/vault/secret.py
@@ -0,0 +1,1 @@
+pass
"""
        return diff, ["src/keprix/vault/secret.py"], None

    request = SelfCodingRequest(
        task="touch vault",
        target_dir="src/keprix/tools/",
        workspace_id="default",
        requested_by="operator",
        run_tests=False,
    )
    result = await run_scoped_mutation(request, store, repo_root, coding_runner=bad_runner)
    assert result.scope_valid is False
    assert result.mutation_id is None
    assert deleted["called"] is True


@pytest.mark.asyncio
async def test_test_failure_saves_staged_with_output(mutation_store, monkeypatch, tmp_path):
    store, _db = mutation_store
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setenv("KEPRIX_MUTATION_SELF_CODING", "true")
    get_mutation_settings.cache_clear()
    _mock_git(monkeypatch, repo_root)

    def good_runner(repo, request, allowed):
        rel = "src/keprix/tools/demo_tool.py"
        diff = f"--- /dev/null\n+++ b/{rel}\n@@ -0,0 +1 @@\n+# demo\n"
        return diff, [rel], None

    monkeypatch.setattr(
        "keprix.mutation.self_coding_harness.run_tests",
        lambda _repo: type("R", (), {"ok": False, "output": "FAILED tests"})(),
    )

    request = SelfCodingRequest(
        task="demo tool",
        target_dir="src/keprix/tools/",
        workspace_id="default",
        requested_by="operator",
    )
    result = await run_scoped_mutation(request, store, repo_root, coding_runner=good_runner)
    assert result.test_passed is False
    assert result.mutation_id is not None
    record = store.get_generated_tool(result.mutation_id)
    assert record is not None
    assert record.status == "staged"
    assert record.metadata.get("test_output") == "FAILED tests"


@pytest.mark.asyncio
async def test_code_mutation_always_staged(mutation_store, monkeypatch, tmp_path):
    store, _db = mutation_store
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setenv("KEPRIX_MUTATION_SELF_CODING", "true")
    get_mutation_settings.cache_clear()
    _mock_git(monkeypatch, repo_root)
    monkeypatch.setattr("keprix.mutation.self_coding_harness.run_tests", lambda _repo: type("R", (), {"ok": True, "output": ""})())

    def good_runner(repo, request, allowed):
        rel = "src/keprix/tools/always_staged.py"
        diff = f"--- /dev/null\n+++ b/{rel}\n@@ -0,0 +1 @@\n+# staged\n"
        return diff, [rel], None

    request = SelfCodingRequest(
        task="always staged",
        target_dir="src/keprix/tools/",
        workspace_id="default",
        requested_by="operator",
    )
    result = await run_scoped_mutation(request, store, repo_root, coding_runner=good_runner)
    record = store.get_generated_tool(result.mutation_id)
    assert record.status == "staged"


@pytest.mark.asyncio
async def test_self_coding_disabled_returns_error(mutation_store, monkeypatch, tmp_path):
    store, _db = mutation_store
    monkeypatch.setenv("KEPRIX_MUTATION_SELF_CODING", "false")
    get_mutation_settings.cache_clear()
    request = SelfCodingRequest(
        task="disabled",
        target_dir="src/keprix/tools/",
        workspace_id="default",
        requested_by="operator",
    )
    result = await run_scoped_mutation(request, store, tmp_path / "repo")
    assert result.success is False
    assert "disabled" in (result.error or "")
