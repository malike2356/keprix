"""Migration writer tests (Prompt 646)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.document_vault.migrate import (
    migrate_knowledge_vault_files,
    migrate_workspace_documents,
)
from keprix.document_vault.service import DocumentVaultService
from keprix.document_vault.storage import LocalStorageAdapter
from keprix.document_vault.store import reset_document_vault_store_for_tests


@pytest.fixture()
def vault(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DocumentVaultService:
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_MIGRATE", "1")
    store = reset_document_vault_store_for_tests(tmp_path / "v.sqlite")
    return DocumentVaultService(store=store, storage=LocalStorageAdapter(root=tmp_path / "blobs"))


def test_migrate_dry_run_does_not_write(
    vault: DocumentVaultService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_MIGRATE", "0")
    docs = [{"id": "d1", "title": "T", "content": "body", "format": "markdown"}]
    report = migrate_workspace_documents("ws", docs, service=vault, dry_run=True)
    assert report["mutated"] is False
    assert vault.store.list_items("ws")["total"] == 0


def test_migrate_workspace_docs_idempotent(vault: DocumentVaultService) -> None:
    docs = [{"id": "d1", "title": "Hello", "content": "# hi", "format": "md"}]
    first = migrate_workspace_documents("ws", docs, service=vault, dry_run=False)
    assert first["created"] == 1
    assert first["mutated"] is True
    second = migrate_workspace_documents("ws", docs, service=vault, dry_run=False)
    assert second["skipped"] == 1
    assert second["created"] == 0
    items = vault.store.list_items("ws")
    assert items["total"] == 1
    mapping = vault.store.get_source_mapping("ws", "workspace_documents", "d1")
    assert mapping
    body = vault.read_text("ws", mapping["item_id"])
    assert body == "# hi"


def test_migrate_knowledge_vault_builds_folders(vault: DocumentVaultService) -> None:
    files = [
        {"path": "notes/a.md", "content": "A"},
        {"path": "notes/b.md", "content": "B"},
    ]
    result = migrate_knowledge_vault_files("ws", files, service=vault, dry_run=False)
    assert result["created"] == 2
    listed = vault.store.search("ws", "a.md")
    assert listed["total"] >= 1
