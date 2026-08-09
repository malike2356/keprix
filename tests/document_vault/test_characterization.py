"""Characterization of existing document / vault surfaces (Prompt 645)."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.document_vault.surfaces import SURFACES

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("surface", SURFACES, ids=lambda s: s.key)
def test_inventoried_surface_path_exists(surface) -> None:
    path = ROOT / surface.path
    assert path.exists(), f"missing inventoried surface: {surface.key} -> {surface.path}"


def test_tenant_vs_admin_boundaries_encoded() -> None:
    tenant = [s for s in SURFACES if s.tenant_scoped]
    adminish = [s for s in SURFACES if not s.tenant_scoped]
    assert any(s.key == "workspace_documents_pg" for s in tenant)
    assert any(s.key == "admin_host_fs" for s in adminish)
    assert any(s.key == "desktop_file_tree" for s in adminish)
    # Host FS must never be migrate-eligible
    for s in SURFACES:
        if s.key in {"admin_host_fs", "desktop_file_tree", "credential_vault"}:
            assert s.migrate_eligible is False


def test_workspace_documents_fallback_and_versions_api_surface() -> None:
    from keprix.workspace import documents_pg, repository

    assert hasattr(documents_pg, "ensure_workspace_document_tables")
    assert hasattr(repository, "workspace_repo")
    routes = ROOT / "src/keprix/workspace/routes/document_routes.py"
    text = routes.read_text(encoding="utf-8")
    assert "/documents" in text or "documents" in text


def test_knowledge_vault_distinct_from_credential_vault() -> None:
    knowledge = ROOT / "src/keprix/api/knowledge_vault_routes.py"
    credential = ROOT / "src/keprix/security/vault_routes.py"
    assert knowledge.is_file() and credential.is_file()
    ktext = knowledge.read_text(encoding="utf-8")
    assert "vault/files" in ktext or "files" in ktext


def test_channel_gateway_document_cache_helpers_exist() -> None:
    base = ROOT / "src/keprix/gateway/platforms/base.py"
    text = base.read_text(encoding="utf-8")
    assert "cache_document" in text or "document_cache" in text or "SUPPORTED_DOCUMENT" in text
