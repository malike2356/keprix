"""Document Vault agent tools Soft Wall and trusted context tests (Prompt 650)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from keprix.document_vault.agent_context import resolve_vault_context
from keprix.document_vault.models import VaultError
from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.soft_wall import gate_vault_action, resolve_vault_approval
from keprix.document_vault.storage import LocalStorageAdapter
from keprix.document_vault.store import reset_document_vault_store_for_tests
from keprix.outreach.ops import reset_outreach_ops_store_for_tests
from keprix.outreach.store import reset_outreach_store_for_tests
from keprix.tools import document_vault_tools as dvt


@pytest.fixture()
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_ENABLED", "1")
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_SOFT_WALL", "1")
    monkeypatch.setenv("KEPRIX_CRM_SOFT_WALL", "1")
    monkeypatch.setenv("KEPRIX_CRM_BACKEND", "sqlite")
    outreach_path = tmp_path / "outreach.sqlite"
    reset_outreach_store_for_tests(outreach_path)
    reset_outreach_ops_store_for_tests(outreach_path)
    store = reset_document_vault_store_for_tests(tmp_path / "vault.sqlite")
    svc = DocumentVaultService(store=store, storage=LocalStorageAdapter(root=tmp_path / "blobs"))
    return store, svc


def _kw(**extra):
    base = {"trusted_workspace_id": "ws-a", "user_id": "actor-1", "session_id": "sess-1"}
    base.update(extra)
    return base


def test_trusted_context_rejects_fabricated_workspace() -> None:
    with pytest.raises(VaultError) as exc:
        resolve_vault_context(
            {"workspace_id": "other"},
            trusted_workspace_id="ws-a",
            user_id="actor-1",
        )
    assert exc.value.code == "workspace_mismatch"


def test_trusted_context_rejects_model_only_workspace() -> None:
    with pytest.raises(VaultError) as exc:
        resolve_vault_context({"workspace_id": "ws-only"})
    assert exc.value.code == "workspace_mismatch"


def test_trusted_context_rejects_host_path() -> None:
    with pytest.raises(VaultError) as exc:
        resolve_vault_context({"path": "/etc/passwd"}, trusted_workspace_id="ws-a")
    assert exc.value.code == "host_fs_forbidden"


def test_public_audience_blocked() -> None:
    with pytest.raises(VaultError) as exc:
        resolve_vault_context({}, trusted_workspace_id="ws-a", audience="public")
    assert exc.value.code == "forbidden"


def test_agent_crud_with_stale_revision(env) -> None:
    _store, _svc = env
    created = json.loads(
        dvt.document_vault_create_file(
            {"name": "Note.md", "content": "v1"},
            **_kw(),
        )
    )
    assert created["ok"] is True
    item_id = created["item"]["id"]
    rev = created["item"]["current_revision"]

    updated = json.loads(
        dvt.document_vault_update(
            {"item_id": item_id, "content": "v2", "expected_revision": rev},
            **_kw(),
        )
    )
    assert updated["ok"] is True

    stale = json.loads(
        dvt.document_vault_update(
            {"item_id": item_id, "content": "v3", "expected_revision": rev},
            **_kw(),
        )
    )
    assert stale.get("error_code") == "stale_revision"

    listed = json.loads(dvt.document_vault_list({}, **_kw()))
    assert listed["ok"] is True
    assert listed["count"] >= 1

    read = json.loads(
        dvt.document_vault_read({"item_id": item_id, "offset": 0, "limit": 1}, **_kw())
    )
    assert read["ok"] is True
    assert read["truncated"] is True
    assert read["content"] == "v"


def test_permanent_delete_requires_soft_wall_then_approval(env) -> None:
    _store, _svc = env
    created = json.loads(
        dvt.document_vault_create_file({"name": "Doomed.md", "content": "x"}, **_kw())
    )
    item_id = created["item"]["id"]
    trashed = json.loads(dvt.document_vault_trash({"item_id": item_id}, **_kw()))
    assert trashed["ok"] is True
    assert trashed["item"]["trashed"] is True

    blocked = json.loads(dvt.document_vault_permanent_delete({"item_id": item_id}, **_kw()))
    assert blocked.get("blocked") is True, blocked
    assert blocked["error_code"] == "soft_wall_required"
    approval = blocked["approval"]
    assert approval and approval.get("id")
    assert "access_token" not in json.dumps(blocked)

    # Pending approval still blocks
    pending = json.loads(
        dvt.document_vault_permanent_delete(
            {"item_id": item_id, "approval_id": approval["id"]},
            **_kw(),
        )
    )
    assert pending["blocked"] is True

    resolve_vault_approval("ws-a", approval["id"], status="approved")
    done = json.loads(
        dvt.document_vault_permanent_delete(
            {"item_id": item_id, "approval_id": approval["id"]},
            **_kw(),
        )
    )
    assert done["ok"] is True


def test_classified_export_and_conflict_overwrite_gates(env) -> None:
    store, _svc = env
    created = json.loads(
        dvt.document_vault_create_file({"name": "Secret.md", "content": "s"}, **_kw())
    )
    item_id = created["item"]["id"]
    updated = store.update_item("ws-a", item_id, classification="secret", bump_revision=False)
    assert updated and updated.get("classification") == "secret"

    blocked = json.loads(dvt.document_vault_export({"item_id": item_id, "format": "md"}, **_kw()))
    assert blocked.get("blocked") is True, blocked
    assert blocked["error_code"] == "soft_wall_required"

    # Conflict overwrite gate unit
    gate = gate_vault_action(
        "ws-a",
        kind="document_vault.conflict_overwrite",
        subject="overwrite",
        payload={"item_id": item_id, "choice": "keep_remote"},
        object_id=item_id,
        actor_id="actor-1",
    )
    assert gate["blocked"] is True


def test_cross_user_workspace_fails_closed(env) -> None:
    created = json.loads(
        dvt.document_vault_create_file({"name": "A.md", "content": "a"}, **_kw())
    )
    item_id = created["item"]["id"]
    # Fabricated workspace in args with different trusted context
    bad = json.loads(
        dvt.document_vault_read(
            {"item_id": item_id, "workspace_id": "ws-b"},
            trusted_workspace_id="ws-a",
            user_id="actor-1",
        )
    )
    assert bad.get("error_code") == "workspace_mismatch"


def test_tools_registered() -> None:
    from tools.registry import registry

    assert registry.get_entry("document_vault_list") is not None
    assert registry.get_entry("document_vault_permanent_delete") is not None
    assert registry.get_entry("document_vault_sync_status") is not None
