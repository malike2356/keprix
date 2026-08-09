from __future__ import annotations

from keprix.tui.command_center.palette import CommandPaletteModel, dispatch_for_action
from keprix.tui.command_center.registry import build_default_registry, document_vault_actions
from keprix.tui.document_vault import format_vault_listing


def test_document_vault_actions_in_registry() -> None:
    registry = build_default_registry()
    assert registry.get("vault:list") is not None
    assert registry.get("vault:host-fs-note") is not None
    assert all(action.kind == "vault" for action in document_vault_actions())


def test_vault_palette_dispatch() -> None:
    model = CommandPaletteModel(build_default_registry(), query="vault list")
    result = model.dispatch_selected()
    assert result is not None
    assert result.dispatch_kind == "vault_action"
    assert result.value == "list"


def test_format_vault_listing_labels_tenant() -> None:
    text = format_vault_listing(
        {"items": [{"id": "a", "kind": "folder", "name": "Reports"}]}
    )
    assert "tenant" in text.lower() or "Document Vault" in text
    assert "Reports" in text
    assert "host filesystem" not in text.lower() or "not host" in text.lower()


def test_host_fs_note_action_exists() -> None:
    action = next(a for a in document_vault_actions() if a.value == "host_fs_note")
    result = dispatch_for_action(action)
    assert result.dispatch_kind == "vault_action"
    assert "host" in action.description.lower() or "separate" in action.description.lower()
