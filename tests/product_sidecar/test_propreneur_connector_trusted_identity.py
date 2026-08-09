"""Prompt 638: product connector CRUD + trusted identity + shared-token disable."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from keprix.product_sidecar.auth import (
    TokenService,
    shared_compat_enabled,
    shared_compat_token_usable,
)
from keprix.product_sidecar.connector import (
    ConnectorDenied,
    FakeProductConnector,
    ProductApiConnector,
    substitute_path,
)
from keprix.product_sidecar.registry import get_product_pack_registry
from keprix.product_sidecar.trusted_context import (
    TrustedExecutionContext,
    merge_trusted_callback_body,
    strip_identity_from_model_args,
)


@pytest.fixture(autouse=True)
def _reset(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KEPRIX_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "test-secret")
    monkeypatch.delenv("KEPRIX_DISABLE_SHARED_COMPAT_TOKEN", raising=False)
    monkeypatch.delenv("KEPRIX_PRODUCT_SIDECAR_DISABLE_SHARED_TOKEN", raising=False)
    get_product_pack_registry().reset_for_tests(install_fixtures=True)


def test_substitute_path_encodes_and_rejects_extra() -> None:
    path = substitute_path(
        "/api/aiva/v1/properties/{propertyId}",
        {"propertyId": "ab/c d"},
    )
    assert path == "/api/aiva/v1/properties/ab%2Fc%20d"
    with pytest.raises(ConnectorDenied, match="missing_path_params"):
        substitute_path("/api/aiva/v1/properties/{propertyId}", {})
    with pytest.raises(ConnectorDenied, match="unexpected_path_params"):
        substitute_path(
            "/api/aiva/v1/properties/{propertyId}",
            {"propertyId": "1", "evil": "x"},
        )


@pytest.mark.asyncio
async def test_propreneur_connector_allows_patch_and_delete_when_declared() -> None:
    conn = ProductApiConnector(
        base_url="",
        routes=list(get_product_pack_registry().require("propreneur").connector["routes"]),
        host_allowlist=["127.0.0.1", "localhost", "*.propreneur.test"],
    )
    patched = await conn.call_manifest(
        method="PATCH",
        path_template="/api/aiva/v1/properties/{propertyId}",
        path_params={"propertyId": "12"},
        json_body={"name": "Updated"},
    )
    assert patched["method"] == "PATCH"
    assert patched["path"] == "/api/aiva/v1/properties/12"

    archived = await conn.archive(
        path_template="/api/aiva/v1/properties/{propertyId}",
        path_params={"propertyId": "12"},
    )
    assert archived["method"] == "DELETE"
    assert archived["path"] == "/api/aiva/v1/properties/12"

    with pytest.raises(ConnectorDenied, match="undeclared_route"):
        conn.assert_allowed("PATCH", "/api/aiva/v1/unknown/{id}")
    with pytest.raises(ConnectorDenied, match="undeclared_or_forbidden"):
        conn.assert_allowed("DELETE", "/admin/users/1")
    with pytest.raises(ConnectorDenied):
        await conn.delete_subject("12")


@pytest.mark.asyncio
async def test_connector_circuit_opens_after_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    conn = FakeProductConnector()
    conn.base_url = "http://127.0.0.1:9"  # force upstream errors

    async def boom(*_a, **_k):
        raise ConnectorDenied("upstream_error:ConnectError")

    # Drive failure counter via real exception path
    original = conn.call

    async def failing_call(*args, **kwargs):
        if conn._circuit_open:
            raise ConnectorDenied("circuit_open")
        conn._circuit_failures += 1
        if conn._circuit_failures >= 5:
            conn._circuit_open = True
        raise ConnectorDenied("upstream_error:ConnectError")

    conn.call = failing_call  # type: ignore[method-assign]
    for _ in range(5):
        with pytest.raises(ConnectorDenied):
            await conn.call("GET", "/api/keprix/v1/health")
    assert conn.circuit_open is True
    with pytest.raises(ConnectorDenied, match="circuit_open"):
        await conn.call("GET", "/api/keprix/v1/health")
    conn.reset_circuit()
    assert conn.circuit_open is False
    conn.call = original  # type: ignore[method-assign]


def test_trusted_context_strips_model_identity_override() -> None:
    trusted = TrustedExecutionContext(
        product="propreneur",
        workspace_id="tenant-A",
        actor_id="7",
        actor_type="tenant_user",
        conversation_id="55",
        correlation_id="corr-1",
    )
    body = merge_trusted_callback_body(
        {"query": "hi", "workspace_id": "tenant-B", "user_id": "999"},
        trusted,
    )
    assert body["workspace_id"] == "tenant-A"
    assert body["user_id"] == "7"
    assert body["query"] == "hi"
    assert "999" not in str(body)
    assert strip_identity_from_model_args({"workspace_id": "x", "q": 1}) == {"q": 1}


def test_shared_compat_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CARINA_KEPRIX_SHARED_TOKEN", "shared-secret")
    monkeypatch.setenv("KEPRIX_PRODUCT_SIDECAR_TOKEN_SECRET", "signing-secret")
    assert shared_compat_enabled() is True
    assert shared_compat_token_usable() == "shared-secret"

    monkeypatch.setenv("KEPRIX_DISABLE_SHARED_COMPAT_TOKEN", "1")
    assert shared_compat_enabled() is False
    assert shared_compat_token_usable() == ""

    svc = TokenService()
    with pytest.raises(ValueError):
        svc.authenticate_request(
            authorization="Bearer shared-secret",
            product="propreneur",
            correlation_id="c1",
        )

    minted, _token = svc.mint(
        product="propreneur",
        deployment="test",
        workspace_id="ws-1",
        actor_id="actor-1",
        grants=frozenset({"node:property_get"}),
        purpose="invoke",
        ttl_seconds=60,
    )
    ctx = svc.authenticate_request(
        authorization=f"Bearer {minted}",
        product="propreneur",
        correlation_id="c2",
    )
    assert ctx.token_mode == "exchange"
    assert ctx.workspace_id == "ws-1"


@pytest.mark.asyncio
async def test_fake_connector_patch_delete_roundtrip() -> None:
    fake = FakeProductConnector()
    out = await fake.call_manifest(
        method="PATCH",
        path_template="/api/aiva/v1/properties/{propertyId}",
        path_params={"propertyId": "42"},
        json_body={"title": "x"},
        headers={"X-Keprix-Trusted-Workspace-Id": "ws-1"},
    )
    assert out["method"] == "PATCH"
    assert out["path"].endswith("/42")
    archived = await fake.archive(
        path_template="/api/aiva/v1/properties/{propertyId}",
        path_params={"propertyId": "42"},
    )
    assert archived["method"] == "DELETE"
