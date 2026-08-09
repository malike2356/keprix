"""Canonical Document Vault domain tests (Prompt 646)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.document_vault.models import VaultError
from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.storage import LocalStorageAdapter
from keprix.document_vault.store import DocumentVaultStore, reset_document_vault_store_for_tests


@pytest.fixture()
def vault(tmp_path: Path) -> DocumentVaultService:
    store = reset_document_vault_store_for_tests(tmp_path / "vault.sqlite")
    storage = LocalStorageAdapter(root=tmp_path / "blobs")
    return DocumentVaultService(store=store, storage=storage)


def test_create_list_read_update_isolation(vault: DocumentVaultService) -> None:
    a = vault.create_text_item("ws_a", "A.md", "# A", kind="markdown", actor_id="u1")
    b = vault.create_text_item("ws_b", "B.md", "# B", kind="markdown", actor_id="u2")
    listed_a = vault.store.list_items("ws_a")
    assert listed_a["total"] == 1
    assert listed_a["items"][0]["id"] == a["id"]
    assert vault.store.get_item("ws_a", b["id"]) is None
    assert vault.read_text("ws_a", a["id"]) == "# A"
    updated = vault.write_content(
        "ws_a",
        a["id"],
        b"# A2",
        expected_revision=a["current_revision"],
        actor_id="u1",
    )
    assert updated["current_revision"] == a["current_revision"] + 1
    assert vault.read_text("ws_a", a["id"]) == "# A2"


def test_stale_revision_rejected(vault: DocumentVaultService) -> None:
    item = vault.create_text_item("ws", "x.md", "one")
    with pytest.raises(VaultError) as ei:
        vault.write_content("ws", item["id"], b"two", expected_revision=0)
    assert ei.value.code == "stale_revision"


def test_cycle_rejected_on_move(vault: DocumentVaultService) -> None:
    root = vault.create_folder("ws", "Root")
    child = vault.create_folder("ws", "Child", parent_id=root["id"])
    with pytest.raises(VaultError) as ei:
        vault.store.move("ws", root["id"], child["id"])
    assert ei.value.code == "cycle_rejected"


def test_trash_restore_and_permanent_delete(vault: DocumentVaultService) -> None:
    folder = vault.create_folder("ws", "Keep")
    doc = vault.create_text_item("ws", "note.md", "hi", parent_id=folder["id"])
    trashed = vault.store.trash("ws", folder["id"])
    assert trashed.get("trashed_at")
    # Cascaded trash hides the child from active queries
    assert vault.store.get_item("ws", doc["id"], include_trashed=False) is None
    child = vault.store.get_item("ws", doc["id"], include_trashed=True)
    assert child and child.get("trashed_at")
    restored = vault.store.restore("ws", folder["id"])
    assert restored.get("trashed_at") is None
    # Child remains trashed until restored; restore child then trash+purge it
    vault.store.restore("ws", doc["id"])
    vault.store.trash("ws", doc["id"])
    gone = vault.store.permanent_delete("ws", doc["id"])
    assert gone["ok"] is True
    assert vault.store.get_item("ws", doc["id"], include_trashed=True) is None


def test_revision_restore(vault: DocumentVaultService) -> None:
    item = vault.create_text_item("ws", "r.md", "v1")
    r1 = item["current_revision"]
    vault.write_content("ws", item["id"], b"v2", expected_revision=r1)
    revs = vault.store.list_revisions("ws", item["id"])
    assert len(revs) >= 2
    restored = vault.restore_revision("ws", item["id"], r1)
    assert vault.read_text("ws", restored["id"]) == "v1"


def test_copy_rename_append_search(vault: DocumentVaultService) -> None:
    item = vault.create_text_item("ws", "alpha.md", "hello")
    copied = vault.store.copy("ws", item["id"], new_name="beta.md")
    assert copied["id"] != item["id"]
    renamed = vault.store.rename("ws", copied["id"], "gamma.md")
    assert renamed["name"] == "gamma.md"
    vault.append_text("ws", item["id"], " world", expected_revision=item["current_revision"])
    assert "hello world" in vault.read_text("ws", item["id"])
    found = vault.store.search("ws", "gamma")
    assert found["total"] >= 1


def test_job_idempotency_and_audit(vault: DocumentVaultService) -> None:
    item = vault.create_folder("ws", "Jobs")
    j1 = vault.store.enqueue_job("ws", "index", item_id=item["id"], idempotency_key="k1")
    j2 = vault.store.enqueue_job("ws", "index", item_id=item["id"], idempotency_key="k1")
    assert j2.get("idempotent") is True
    assert j1["id"] == j2["id"]
    events = vault.store.list_audit("ws")
    assert events


def test_path_traversal_name_rejected(vault: DocumentVaultService) -> None:
    item = vault.create_folder("ws", "../etc/passwd")
    assert "/" not in item["name"]
    assert "\\" not in item["name"]
    assert item["name"] != "../etc/passwd"


def test_sqlite_and_service_offline_ce(tmp_path: Path) -> None:
    """Community Edition local sqlite works without network/Postgres."""
    store = DocumentVaultStore(path=tmp_path / "ce.sqlite", backend="sqlite")
    svc = DocumentVaultService(store=store, storage=LocalStorageAdapter(root=tmp_path / "b"))
    item = svc.create_text_item("local", "ce.md", "offline")
    assert item["checksum"]
    assert svc.read_text("local", item["id"]) == "offline"
