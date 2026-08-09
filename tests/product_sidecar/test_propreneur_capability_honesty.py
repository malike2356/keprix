"""Honesty tests: executable labels require handler, route, method, and tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from keprix.product_sidecar.honesty import (
    apply_fail_closed_statuses,
    assert_live_nodes_honest,
    has_executable_handler,
    resolve_fail_closed_status,
)
from keprix.product_sidecar.invoke import invoke_node
from keprix.product_sidecar.packs.propreneur import build_propreneur_nodes
from keprix.product_sidecar.packs.propreneur_ops import EXECUTABLE_HTTP_NODES, LIVE_PROPERTY_NODES
from keprix.product_sidecar.registry import (
    _propreneur_connector,
    build_propreneur_pack,
    get_product_pack_registry,
)
from keprix.product_sidecar.types import CapabilityNode, NodeStatus, RequestContext


@pytest.fixture(autouse=True)
def _reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "test-secret")
    monkeypatch.delenv("PROPRENEUR_PRODUCT_API_URL", raising=False)
    get_product_pack_registry().reset_for_tests(install_fixtures=True)


def test_property_get_is_live_with_handler_route_and_test() -> None:
    pack = build_propreneur_pack()
    node = pack.nodes["property_get"]
    assert has_executable_handler("property_get") is True
    assert node.status == NodeStatus.LIVE


def test_executable_http_nodes_are_honest() -> None:
    pack = build_propreneur_pack()
    violations = assert_live_nodes_honest(pack.nodes.values(), connector=pack.connector)
    assert violations == []
    assert pack.node_status_counts().get("live", 0) >= 20
    assert pack.node_status_counts().get("approval_required", 0) >= 20
    for key in LIVE_PROPERTY_NODES:
        assert pack.nodes[key].status in {NodeStatus.LIVE, NodeStatus.APPROVAL_REQUIRED}
    assert pack.nodes["compliance_propose"].status == NodeStatus.PROPOSAL_ONLY
    assert pack.nodes["task_create"].status == NodeStatus.NOT_CONFIGURED


def test_declared_live_without_handler_is_downgraded() -> None:
    raw = build_propreneur_nodes()
    forced: dict[str, CapabilityNode] = {}
    for key, node in raw.items():
        status = NodeStatus.LIVE if key == "task_create" else node.status
        forced[key] = CapabilityNode(
            key=node.key,
            version=node.version,
            title=node.title,
            product=node.product,
            domain=node.domain,
            risk=node.risk,
            status=status,
            required_grants=node.required_grants,
            entitlements=node.entitlements,
            soft_wall=node.soft_wall,
            sync=node.sync,
            input_schema=dict(node.input_schema),
            output_schema=dict(node.output_schema),
            timeout_seconds=node.timeout_seconds,
            budget_units=node.budget_units,
            idempotent=node.idempotent,
            operator_guidance=node.operator_guidance,
            aiva_sku_ok=node.aiva_sku_ok,
            carina_admin_only=node.carina_admin_only,
        )
    honest = apply_fail_closed_statuses(forced, connector=_propreneur_connector())
    assert honest["task_create"].status == NodeStatus.NOT_CONFIGURED
    assert resolve_fail_closed_status("task_create", NodeStatus.LIVE) == NodeStatus.NOT_CONFIGURED
    assert resolve_fail_closed_status(
        "property_get",
        NodeStatus.NOT_CONFIGURED,
        connector=_propreneur_connector(),
    ) == NodeStatus.LIVE


@pytest.mark.asyncio
async def test_property_get_invoke_no_longer_501() -> None:
    ctx = RequestContext(
        product="propreneur",
        deployment="test",
        workspace_id="ws-tenant-1",
        actor_id="user-1",
        grants=frozenset({"node:property_get", "*"}),
        purpose="test",
        correlation_id="corr-640",
    )
    result = await invoke_node(ctx, node_key="property_get", input_payload={"propertyId": "p1"})
    assert result.get("ok") is True
    assert result.get("node") == "property_get"
    assert result.get("code") != "not_configured"
    inner = result.get("result") or {}
    assert inner.get("status") == "completed"


@pytest.mark.asyncio
async def test_proposal_only_and_forbidden_honest() -> None:
    ctx = RequestContext(
        product="propreneur",
        deployment="test",
        workspace_id="ws-tenant-1",
        actor_id="user-1",
        grants=frozenset({"*"}),
        purpose="test",
        correlation_id="corr-640b",
    )
    proposal = await invoke_node(ctx, node_key="expense_propose", input_payload={"amount": 10})
    assert proposal.get("code") == "proposal_only"

    # Intentionally forbidden ops are contract-only (no pack node); proxy remains classified.


def test_health_reports_domain_coverage() -> None:
    registry = get_product_pack_registry()
    health = registry.health("propreneur")
    assert health["node_counts"].get("live", 0) >= 20
    assert health["node_counts"].get("approval_required", 0) >= 20
    assert health["node_counts"].get("proposal_only", 0) >= 5
    assert health["node_counts"].get("not_configured", 0) <= 5
    assert health.get("capability_honesty") == "fail_closed_remediation"
    # Nested tasks / notes / sync remain not_configured until typed routes exist.
    assert health.get("crud_complete") is False
    assert len(EXECUTABLE_HTTP_NODES) >= 40
