"""Tests for code mutation API routes (Prompt 153)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from keprix.api.server import create_app
from keprix.mutation.config import get_mutation_settings
from keprix.mutation.store import MutationStore
from keprix.public_api.auth import require_developer_session


@pytest.fixture
def mutation_store(tmp_path, monkeypatch):
    get_mutation_settings.cache_clear()
    monkeypatch.setattr("keprix.database.get_session_factory", lambda: None)
    monkeypatch.setattr("keprix.mutation.store.get_session_factory", lambda: None)
    store = MutationStore(sqlite_path=tmp_path / "mutation.db")
    monkeypatch.setattr("keprix.mutation.store._store", store)
    monkeypatch.setattr("keprix.mutation.store.get_mutation_store", lambda: store)
    return store


@pytest.fixture
def client(mutation_store, monkeypatch):
    app = create_app()

    async def _auth() -> str:
        return "dev"

    app.dependency_overrides[require_developer_session] = _auth
    monkeypatch.setattr(
        "keprix.mutation.routes.effective_access_level",
        lambda: "admin",
    )
    return TestClient(app)


def test_request_returns_403_when_disabled(client, monkeypatch):
    monkeypatch.setenv("KEPRIX_MUTATION_SELF_CODING", "false")
    get_mutation_settings.cache_clear()
    response = client.post(
        "/api/mutation/code/request",
        json={"task": "create tool", "target_dir": "src/keprix/tools/"},
    )
    assert response.status_code == 403


def test_request_returns_202_when_enabled(client, mutation_store, monkeypatch):
    monkeypatch.setenv("KEPRIX_MUTATION_SELF_CODING", "true")
    get_mutation_settings.cache_clear()

    async def fake_run(request, store, repo_root, coding_runner=None):
        from keprix.mutation.self_coding_harness import SelfCodingResult

        return SelfCodingResult(
            success=True,
            mutation_id="code-123",
            branch_name="mutation/test/demo",
            diff="diff",
            test_output="ok",
            test_passed=True,
            scope_valid=True,
            error=None,
            files_changed=["src/keprix/tools/demo.py"],
        )

    monkeypatch.setattr("keprix.mutation.self_coding_harness.run_scoped_mutation", fake_run)
    response = client.post(
        "/api/mutation/code/request",
        json={"task": "create tool", "target_dir": "src/keprix/tools/"},
    )
    assert response.status_code == 202
    assert response.json()["mutation_id"] == "code-123"


def test_diff_endpoint_returns_unified_diff(client, mutation_store):
    record = mutation_store.save_mutation_event(
        workspace_id="default",
        tier="code",
        trigger="operator",
        status="staged",
        name="demo",
        description="demo",
        source_code="--- a/file\n+++ b/file\n",
        metadata={"branch_name": "mutation/x"},
    )
    response = client.get(f"/api/mutation/code/{record.id}/diff")
    assert response.status_code == 200
    assert "diff" in response.json()


def test_approve_merges_branch(client, mutation_store, monkeypatch):
    record = mutation_store.save_mutation_event(
        workspace_id="default",
        tier="code",
        trigger="operator",
        status="staged",
        name="demo",
        description="demo",
        source_code="diff",
        metadata={"branch_name": "mutation/x", "files_changed": []},
    )
    from keprix.mutation import self_coding_git

    monkeypatch.setattr(
        self_coding_git,
        "merge_mutation_branch",
        lambda *args, **kwargs: self_coding_git.GitCommandResult(ok=True, commit_hash="abc123"),
    )
    response = client.post(f"/api/mutation/code/{record.id}/approve")
    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_reject_deletes_branch(client, mutation_store, monkeypatch):
    record = mutation_store.save_mutation_event(
        workspace_id="default",
        tier="code",
        trigger="operator",
        status="staged",
        name="demo",
        description="demo",
        source_code="diff",
        metadata={"branch_name": "mutation/x"},
    )
    deleted = {"called": False}

    def fake_cleanup(self, rec):
        deleted["called"] = True

    monkeypatch.setattr(MutationStore, "_cleanup_code_branch", fake_cleanup)
    response = client.post(f"/api/mutation/code/{record.id}/reject", json={"reason": "nope"})
    assert response.status_code == 200
    assert response.json()["status"] == "rejected"
    assert deleted["called"] is True


def test_rollback_reverts_merged_commit(client, mutation_store, monkeypatch):
    record = mutation_store.save_mutation_event(
        workspace_id="default",
        tier="code",
        trigger="operator",
        status="approved",
        name="demo",
        description="demo",
        source_code="diff",
        metadata={"branch_name": "mutation/x", "merged": True, "merge_commit_hash": "abc123"},
    )
    reverted = {"called": False}

    def fake_rollback(self, rec):
        reverted["called"] = True

    monkeypatch.setattr(MutationStore, "_rollback_code_mutation", fake_rollback)
    response = client.post(f"/api/mutation/code/{record.id}/rollback")
    assert response.status_code == 200
    assert reverted["called"] is True
