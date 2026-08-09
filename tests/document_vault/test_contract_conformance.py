"""Document Vault contract conformance (Prompt 645).

Locks shared behavioral contract alignment and proves no Carina runtime
dependency. document_vault_ready stays false until Prompt 653.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SHARED = Path("/opt/lampp/htdocs/verlox/shared/workspace-governance/AIVA-KEPRIX-DOCUMENT-VAULT.md")
MATRIX = ROOT / "docs/architecture/document-vault-capability-matrix.md"
CONTRACT = ROOT / "docs/architecture/document-vault-contract.md"
OWNERSHIP = ROOT / "docs/architecture/document-vault-ownership-and-migration.md"
SCHEMA = ROOT / "schemas/document-vault/contract.schema.json"
PKG = ROOT / "src/keprix/document_vault"

DOCUMENT_VAULT_READY = False


def test_shared_and_keprix_contract_docs_exist() -> None:
    assert SHARED.is_file()
    assert MATRIX.is_file()
    assert CONTRACT.is_file()
    assert OWNERSHIP.is_file()
    assert SCHEMA.is_file()
    shared = SHARED.read_text(encoding="utf-8")
    assert "Document Vault" in shared
    assert "Keprix implements the same behavioral contract" in shared
    assert "host filesystem" in shared.lower()
    keprix = CONTRACT.read_text(encoding="utf-8")
    assert "carina_runtime_required" in keprix
    assert "**false**" in keprix.lower() or "false" in keprix


def test_schema_version_flags_and_readiness() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    assert schema["properties"]["contract_version"]["const"] == "1.0.0"
    assert schema["properties"]["product"]["const"] == "keprix"
    assert schema["properties"]["carina_runtime_required"]["const"] is False
    flags = schema["properties"]["flags"]["properties"]
    assert flags["KEPRIX_DOCUMENT_VAULT_HOST_FS_BRIDGE"]["const"] is False
    assert DOCUMENT_VAULT_READY is False
    assert "document_vault_ready" in schema["properties"]


def test_required_item_kinds_match_shared_contract() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    kinds = set(schema["properties"]["item_kinds"]["items"]["enum"])
    required = {
        "folder",
        "rich_document",
        "spreadsheet",
        "presentation",
        "markdown",
        "html",
        "plain_text",
        "pdf",
        "binary_upload",
    }
    assert required <= kinds
    authority = set(schema["properties"]["content_authority"]["items"]["enum"])
    assert authority == {"workspace", "google"}


def test_package_declares_no_carina_runtime() -> None:
    from keprix import document_vault

    assert document_vault.CARINA_RUNTIME_REQUIRED is False
    assert document_vault.PRODUCT == "keprix"
    assert document_vault.CONTRACT_VERSION == "1.0.0"


def test_document_vault_package_has_no_carina_imports() -> None:
    """Static scan: document_vault must not import Carina modules."""
    offenders: list[str] = []
    for path in PKG.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "carina" or alias.name.startswith("carina."):
                        offenders.append(f"{path.name}: import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if mod == "carina" or mod.startswith("carina."):
                    offenders.append(f"{path.name}: from {mod}")
    assert offenders == []


def test_matrix_lists_build_order_and_host_fs_out_of_scope() -> None:
    text = MATRIX.read_text(encoding="utf-8")
    for prompt in ("645", "646", "647", "648", "649", "650", "651", "652", "653"):
        assert prompt in text
    assert "OUT_OF_SCOPE" in text
    assert "/api/fs" in text
    assert "MISSING" in text  # canonical service still missing until 646


def test_flags_force_host_fs_bridge_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_HOST_FS_BRIDGE", "1")
    monkeypatch.setenv("KEPRIX_DOCUMENT_VAULT_ENABLED", "1")
    from keprix.document_vault.flags import load_flags

    flags = load_flags()
    assert flags.host_fs_bridge is False
    assert flags.enabled is True


def test_fs_adapter_never_routes_to_vault() -> None:
    from keprix.document_vault.compatibility import adapter_routing_allowed

    result = adapter_routing_allowed("/api/fs/list")
    assert result["ok"] is False
    assert result["error_code"] == "host_fs_forbidden"
