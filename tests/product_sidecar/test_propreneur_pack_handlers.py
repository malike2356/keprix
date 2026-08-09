"""Prompt 639-640: Propreneur domain handlers + FakeProductConnector conformance."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from keprix.agent.carina_bridge import CarinaAgentBridge, CarinaToolRegistry, LlmTurn, ProviderPool, SessionStore
from keprix.product_sidecar.connector import FakeProductConnector
from keprix.product_sidecar.generated import load_propreneur_connector_routes, load_propreneur_pack_nodes
from keprix.product_sidecar.handlers import HANDLERS
from keprix.product_sidecar.honesty import BEHAVIORAL_TEST_NODES, has_executable_handler
from keprix.product_sidecar.invoke import invoke_node
from keprix.product_sidecar.packs.propreneur_ops import (
    EXECUTABLE_HTTP_NODES,
    execute_propreneur_node,
    resolve_pack_node,
)
from keprix.product_sidecar.registry import build_propreneur_pack, get_product_pack_registry
from keprix.product_sidecar.state import get_approval_store, input_hash
from keprix.product_sidecar.trusted_context import TrustedExecutionContext
from keprix.product_sidecar.types import NodeStatus, RequestContext


@pytest.fixture(autouse=True)
def _reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "test-secret")
    monkeypatch.delenv("PROPRENEUR_PRODUCT_API_URL", raising=False)
    get_product_pack_registry().reset_for_tests(install_fixtures=True)
    get_approval_store().reset_for_tests()


def _ctx(**kwargs: object) -> RequestContext:
    base = dict(
        product="propreneur",
        deployment="test",
        workspace_id="ws-tenant-1",
        actor_id="user-1",
        grants=frozenset({"*"}),
        purpose="test",
        correlation_id="corr-640",
    )
    base.update(kwargs)
    return RequestContext(**base)  # type: ignore[arg-type]


def _fake() -> FakeProductConnector:
    routes = list(load_propreneur_connector_routes().get("routes") or [])
    return FakeProductConnector(product_key="propreneur", extra_routes=routes)


def _catalog() -> dict[str, dict]:
    return {str(n["key"]): n for n in load_propreneur_pack_nodes().get("nodes") or []}


async def _approve_and_payload(node_key: str, payload: dict) -> dict:
    store = get_approval_store()
    control_keys = {
        "approval_id",
        "approval_token",
        "idempotency_key",
        "correlation_id",
        "etag",
        "if_match",
        "tool_call_id",
    }
    ih = input_hash({k: v for k, v in payload.items() if k not in control_keys})
    row = store.request(
        product="propreneur",
        workspace_id="ws-tenant-1",
        node_key=node_key,
        input_hash=ih,
        reason=f"test {node_key}",
        deep_link="/test",
    )
    store.decide(row["approval_id"], workspace_id="ws-tenant-1", approved=True, actor_id="user-1")
    out = dict(payload)
    out["approval_id"] = row["approval_id"]
    return out


def _sample_payload(node: dict) -> dict:
    path = str(node.get("http_path") or "")
    method = str(node.get("http_method") or "").upper()
    payload: dict = {}
    if "{propertyId}" in path:
        payload["propertyId"] = "11"
    if "{contactId}" in path:
        payload["contactId"] = "22"
    if "{tenancyId}" in path:
        payload["tenancyId"] = "33"
    if "{dealId}" in path:
        payload["dealId"] = "44"
    if "{ticketId}" in path:
        payload["ticketId"] = "55"
    if "{projectId}" in path:
        payload["projectId"] = "66"
    if "{leadId}" in path:
        payload["leadId"] = "77"
    if "{documentId}" in path:
        payload["documentId"] = "88"
    if "{expenseId}" in path:
        payload["expenseId"] = "99"
    if "{appointmentId}" in path:
        payload["appointmentId"] = "101"
    if method in {"POST", "PATCH"}:
        payload.setdefault("name", f"sample-{node['key']}")
    return payload


@pytest.mark.asyncio
async def test_every_executable_http_node_fake_connector_conformance() -> None:
    catalog = _catalog()
    fake = _fake()
    for node_key in sorted(EXECUTABLE_HTTP_NODES):
        assert node_key in HANDLERS
        assert node_key in BEHAVIORAL_TEST_NODES
        assert has_executable_handler(node_key)
        node = catalog[node_key]
        method = str(node["http_method"]).upper()
        path_template = str(node["http_path"])
        payload = _sample_payload(node)
        if bool(node.get("soft_wall")):
            payload = await _approve_and_payload(node_key, payload)
        trusted = TrustedExecutionContext(
            product="propreneur",
            workspace_id="ws-tenant-1",
            actor_id="user-1",
            actor_type="tenant_user",
            correlation_id="corr-640",
            granted_scopes=("*",),
            idempotency_key=f"idem-{node_key}-{uuid.uuid4().hex[:10]}",
        )
        result = await execute_propreneur_node(
            _ctx(),
            node_key,
            payload,
            connector=fake,
            trusted=trusted,
        )
        assert result["success"] is True, node_key
        assert result["status"] == "completed", node_key
        assert result["method"] == method, node_key
        assert result["node"] == node_key
        action = fake.actions[-1]
        assert action["method"] == method
        assert action["headers"].get("X-Keprix-Trusted-Workspace-Id") == "ws-tenant-1"
        assert "{" not in action["path"]


@pytest.mark.asyncio
async def test_property_create_soft_wall_pending_before_approval() -> None:
    result = await execute_propreneur_node(
        _ctx(),
        "property_create",
        {"name": "Pending Flat"},
        connector=_fake(),
    )
    assert result["success"] is False
    assert result["status"] == "awaiting_approval"
    assert "/propreneur/soft-wall" in str(result["approval"]["deep_link"])


@pytest.mark.asyncio
async def test_invoke_and_adapter_share_normalized_success() -> None:
    pack = build_propreneur_pack()
    assert pack.nodes["property_get"].status == NodeStatus.LIVE
    assert pack.nodes["contact_get"].status == NodeStatus.LIVE
    assert pack.nodes["tenancy_create"].status == NodeStatus.APPROVAL_REQUIRED

    result = await invoke_node(
        _ctx(grants=frozenset({"node:contact_get", "*"})),
        node_key="contact_get",
        input_payload={"contactId": "22"},
    )
    assert result.get("ok") is True
    inner = result.get("result") or {}
    assert inner.get("success") is True
    assert inner.get("path") == "/api/aiva/v1/contacts/22"


@pytest.mark.asyncio
async def test_chat_tool_loop_routes_through_adapter_and_pauses_on_pending() -> None:
    calls = {"n": 0}

    async def fake_complete(**_kwargs):  # type: ignore[no-untyped-def]
        calls["n"] += 1
        if calls["n"] == 1:
            return LlmTurn(
                content=None,
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "property_create",
                            "arguments": json.dumps({"name": "Chat Flat"}),
                        },
                    }
                ],
                finish_reason="tool_calls",
                usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            )
        return LlmTurn(
            content="Created the property successfully.",
            tool_calls=[],
            finish_reason="stop",
            usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
        )

    bridge = CarinaAgentBridge(
        provider_pool=ProviderPool(complete_fn=fake_complete, fallbacks=[]),
        session_store=SessionStore(),
        max_iterations=3,
        timeout_seconds=30,
    )
    out = await bridge.run(
        workspace_id="ws-tenant-1",
        session_id="sess-640",
        model="test",
        temperature=0,
        system_prompt="You are the Propreneur agent.",
        messages=[{"role": "user", "content": "Create a property"}],
        tools=[],
        carina_tools=[
            {
                "name": "property_create",
                "http_endpoint": "http://127.0.0.1:9/unused",
                "parameters": {"type": "object", "properties": {"name": {"type": "string"}}},
                "workspace_id": "ws-tenant-1",
                "user_id": "user-1",
                "product": "propreneur",
            }
        ],
        product="propreneur",
        inject_worker_kb=False,
        escalation_enabled=False,
    )
    assert calls["n"] == 1
    assert out["finish_reason"] == "awaiting_approval"
    assert out["actions"][0]["status"] == "awaiting_approval"


@pytest.mark.asyncio
async def test_registry_execute_alias_uses_adapter() -> None:
    registry = CarinaToolRegistry()
    trusted = TrustedExecutionContext(
        product="propreneur",
        workspace_id="ws-tenant-1",
        actor_id="user-1",
        actor_type="tenant_user",
        correlation_id="corr-chat",
        granted_scopes=("*",),
    )
    registry.register_http_tool(
        name="get_contact",
        endpoint="http://127.0.0.1:9/unused",
        schema={"type": "object", "properties": {"contactId": {"type": "string"}}},
        trusted=trusted,
    )
    assert resolve_pack_node("get_contact") == "contact_get"
    text = await registry.execute("get_contact", {"contactId": "p1", "workspace_id": "evil"})
    payload = json.loads(text)
    assert payload["success"] is True
    assert payload["node"] == "contact_get"


def test_domain_status_vocabulary() -> None:
    pack = build_propreneur_pack()
    assert pack.nodes["document_search"].status == NodeStatus.LIVE
    assert pack.nodes["expense_get"].status == NodeStatus.LIVE
    assert pack.nodes["expense_propose"].status == NodeStatus.PROPOSAL_ONLY
    assert pack.nodes["appointment_cancel"].status == NodeStatus.APPROVAL_REQUIRED
    assert pack.node_status_counts().get("live", 0) + pack.node_status_counts().get(
        "approval_required", 0
    ) == len(EXECUTABLE_HTTP_NODES)
