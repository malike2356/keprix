"""Prompt 272 Hub catalog test."""

from __future__ import annotations

from keprix.hub.registry import get_pack_registry


def test_obsidian_starter_pack_appears_in_hub_catalog() -> None:
    manifests = get_pack_registry().discover_catalog()

    assert any(manifest.name == "obsidian-vault-starter" for manifest in manifests)
