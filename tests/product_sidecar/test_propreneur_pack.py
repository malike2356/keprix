"""Acceptance tests for the Propreneur product sidecar pack."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.product_sidecar.packs.propreneur import build_propreneur_nodes
from keprix.product_sidecar.provision import plan_provision, provision_product
from keprix.product_sidecar.registry import (
    PackValidationError,
    build_propreneur_pack,
    get_product_pack_registry,
    validate_pack,
)
from keprix.product_sidecar.types import CapabilityNode, NodeStatus, RiskClass


@pytest.fixture(autouse=True)
def _reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "test-secret")
    get_product_pack_registry().reset_for_tests(install_fixtures=True)


def test_pack_installs_with_expected_nodes_and_namespace() -> None:
    registry = get_product_pack_registry()
    pack = registry.require("propreneur")
    assert pack.product_key == "propreneur"
    assert pack.memory_namespace == "product:propreneur"
    assert pack.pack_id == "propreneur-sidecar"
    assert pack.contract_version == "1.0.0"
    assert pack.enabled is True

    expected = {
        "property_search",
        "property_get",
        "property_create",
        "property_update",
        "property_archive",
        "contact_search",
        "contact_get",
        "contact_create",
        "contact_update",
        "tenancy_search",
        "tenancy_get",
        "tenancy_create",
        "tenancy_update",
        "deal_search",
        "deal_get",
        "deal_propose",
        "compliance_get",
        "compliance_propose",
        "maintenance_search",
        "maintenance_propose",
        "expense_propose",
        "financial_log_propose",
        "team_invite_propose",
        "task_create",
        "note_create",
        "ask_portfolio",
        "sync_health",
    }
    assert set(pack.nodes) == expected

    nodes = build_propreneur_nodes()
    assert nodes["property_get"].risk == RiskClass.READ
    assert nodes["property_create"].risk == RiskClass.MUTATE
    assert nodes["property_create"].soft_wall is True
    assert nodes["property_archive"].risk == RiskClass.DESTRUCTIVE
    assert nodes["property_archive"].soft_wall is True
    assert nodes["deal_propose"].risk == RiskClass.PROPOSE
    assert nodes["deal_propose"].soft_wall is True
    assert nodes["ask_portfolio"].risk == RiskClass.READ
    assert nodes["ask_portfolio"].soft_wall is False
    assert all(n.status == NodeStatus.LIVE for n in nodes.values())


def test_cross_product_node_denied() -> None:
    registry = get_product_pack_registry()
    pack = build_propreneur_pack()
    evil = dict(pack.nodes)
    evil["evil.cross"] = CapabilityNode(
        key="evil.cross",
        version="1.0.0",
        title="foreign node",
        product="abbis",
        domain="fixture",
        risk=RiskClass.HIGH_RISK,
        status=NodeStatus.LIVE,
        required_grants=("*",),
    )
    pack.nodes = evil
    with pytest.raises(PackValidationError, match="cross_product_node"):
        validate_pack(pack, installed={p.product_key: p for p in [
            registry.require(k) for k in registry.known_products() if k != "propreneur"
        ]})

    with pytest.raises(PermissionError):
        registry.compose_nodes("propreneur", "abbis")


def test_health_and_capabilities_via_registry() -> None:
    registry = get_product_pack_registry()
    health = registry.health("propreneur")
    assert health["product"] == "propreneur"
    assert health["enabled"] is True
    assert health["contract_version"] == "1.0.0"
    assert health["node_counts"].get("live", 0) >= 19

    public = registry.inspect("propreneur")
    assert public["product_key"] == "propreneur"
    assert public["memory_namespace"] == "product:propreneur"
    assert "property_search" in public["nodes"]

    connector = registry.require("propreneur").connector
    assert connector["base_url_env"] == "PROPRENEUR_PRODUCT_API_URL"
    assert "127.0.0.1" in connector["host_allowlist"]
    assert "*.propreneur.test" in connector["host_allowlist"]
    paths = {r["path"] for r in connector["routes"]}
    assert "/api/keprix/v1/health" in paths
    assert "/api/carina/tools" in paths
    assert "/api/carina/tools/{toolName}" in paths


def test_provision_dry_run_works() -> None:
    plan = plan_provision("propreneur")
    assert plan["product_key"] == "propreneur"
    assert plan["dry_run"] is True
    assert plan["idempotent"] is True
    assert any(step["id"] == "pack" for step in plan["steps"])

    dry = provision_product("propreneur", dry_run=True)
    assert dry["status"] == "planned"
    assert dry["checks"][0]["status"] == "ok"
